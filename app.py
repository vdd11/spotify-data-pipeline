import requests
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup
import re
from datetime import datetime

def run_pipeline():
    # --- STEP 2: Download HTML ---
    url = "https://en.wikipedia.org/wiki/List_of_most-streamed_songs_on_Spotify"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    print("Fetching data from Wikipedia...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return

    # --- STEP 3: Transform with BeautifulSoup ---
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'class': 'wikitable'})
    
    data = []
    for row in table.find_all('tr'):
        cols = [ele.text.strip() for ele in row.find_all(['td', 'th'])]
        data.append(cols)

    df = pd.DataFrame(data[1:], columns=data[0])

    # --- STEP 4: Process & Clean Data ---
    # Clean headers and remove Wikipedia citations
    df.columns = [re.sub(r'\[.*?\]', '', str(col)).replace('(s)', '').strip() for col in df.columns]
    
    def clean_val(text):
        return re.sub(r'\[.*?\]', '', str(text)).replace('"', '').strip()

    df['Song'] = df['Song'].apply(clean_val)
    df['Artist'] = df['Artist'].apply(clean_val)
    
    # Convert Streams to numeric (4th column)
    df['Streams (billions)'] = df.iloc[:, 3].apply(lambda x: re.sub(r'[^\d.]', '', clean_val(x)))
    df['Streams (billions)'] = pd.to_numeric(df['Streams (billions)'], errors='coerce')
    
    # Extract Year
    df['Release Year'] = df.iloc[:, 4].apply(lambda x: re.search(r'\d{4}', clean_val(x)).group() if re.search(r'\d{4}', clean_val(x)) else None)
    df['scraping_date'] = datetime.now().strftime('%Y-%m-%d')

    # --- STEP 5: SQLite Storage ---
    conn = sqlite3.connect('spotify.db')
    df.to_sql('daily_rankings', conn, if_exists='replace', index=False)
    conn.commit()
    print("Database updated: spotify.db")

    # --- STEP 6: Visualization ---
    plt.style.use('ggplot')
    plt.figure(figsize=(10, 6))
    top_10 = df.nlargest(10, 'Streams (billions)')
    plt.barh(top_10['Song'], top_10['Streams (billions)'], color='teal')
    plt.xlabel('Streams (Billions)')
    plt.title('Top 10 Most Streamed Songs on Spotify')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig('top_10_streams.png') # Save for GitHub preview
    plt.show()
    conn.close()

if __name__ == "__main__":
    run_pipeline()
