# -*- coding: utf-8 -*-
"""Busca de podcast e episódios no Spotify
Criado por Gerardo Felipe Espinoza Pérez em 15/11/2023 para o GISDay 2023
com o apoio de ChatGPT
"""

#Credenciais da Spotify API
#Para entender melhor como criar as credenciais, acesse https://developer.spotify.com/documentation/web-api/concepts/apps
client_id = 'XXXXXXXXXXXXXXXXXXXXXXXXXXX'
client_secret = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXX'

#Parametros de entrada
keywords = 'Sensoriamento Remoto'
podcast_qtd = 1
episodes_qtd = 5

#importa bilbiotecas
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
from PIL import Image
from io import BytesIO

# Inicializa o Cliet Spotify
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

search_results = sp.search(q=keywords,limit=podcast_qtd,type='show',market='BR')

if search_results and 'shows' in search_results:
    print(f"Podcasts encontrados:")
    for idx, item in enumerate(search_results['shows']['items'], start=1):
        print(f"{idx}. {item['name']} - URI: {item['uri']}")

        episodes = sp.show_episodes(item['uri'],limit=episodes_qtd)
        if episodes and 'items' in episodes:
            for episode_idx, episode in enumerate(episodes['items'], start=1):
                episode_name = episode['name']
                episode_duration_ms = episode['duration_ms']
                episode_duration = f"{int(episode_duration_ms / 60000)}:{int((episode_duration_ms / 1000) % 60):02}"
                print(f"  Ep.{episode_idx}: {episode_name} - Duração: {episode_duration}")
        else:
            print("Não foram encontrados episódios para este podcast")
        print("\n")
else:
    print(f"Não foram encontrados podcasts com a expressão: '{keywords}'")