import praw
from datetime import datetime, timedelta, timezone
import google.generativeai as genai
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
import plotly.graph_objects as go
from textblob import TextBlob
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

genai.configure(api_key="Mettre ses infos personnels")

# Initialisation du modèle Gemini
gemini_model = genai.GenerativeModel("gemini-1.5-pro-latest")


reddit = praw.Reddit(
    client_id='Mettre ses infos personnels',              
    client_secret='Mettre ses infos personnels',       
    user_agent='Mettre ses infos personnels',
    username='Mettre ses infos personnels',
    password='Mettre ses infos personnels'
)

subreddit = reddit.subreddit('python')


def chercher_avis(mot_cle, limite=1000):
    maintenant = datetime.now(timezone.utc)
    posts_24h, posts_1w, posts_1m = [], [], []

    # D'abord, les tout récents (moins de 24h)
    for post in reddit.subreddit("all").search(mot_cle, sort='new', time_filter='day', limit=int(limite / 3)):
        date_post = datetime.fromtimestamp(post.created_utc, timezone.utc)
        age = maintenant - date_post

        info = {
            'titre': post.title,
            'url': post.url,
            'score': post.score,
            'date': date_post.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if age <= timedelta(days=1):
            posts_24h.append(info)

    # Ensuite, les posts plus anciens (jusqu'à un mois)
    for post in reddit.subreddit("all").search(mot_cle, sort='relevance', time_filter='month', limit=int(limite * 2 / 3)):
        date_post = datetime.fromtimestamp(post.created_utc, timezone.utc)
        age = maintenant - date_post

        info = {
            'titre': post.title,
            'url': post.url,
            'score': post.score,
            'date': date_post.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if timedelta(days=1) < age <= timedelta(days=7):
            posts_1w.append(info)
        elif timedelta(days=7) < age <= timedelta(days=30):
            posts_1m.append(info)

    return {
        "il_y_a_24h": posts_24h,
        "il_y_a_une_semaine": posts_1w,
        "il_y_a_un_mois": posts_1m
    }

def generer_prompt_pour_gemini(mot_cle, limite=1000):
    avis = chercher_avis(mot_cle, limite)

    def formatter_posts(posts):
        return "\n".join([f"- {post['titre']}" for post in posts]) or "Aucun commentaire."

    prompt = f"""
Analyse l'évolution des sentiments parmi les commentaires suivants, organisés par période. 
Indique si les sentiments deviennent plus positifs, plus négatifs ou restent stables, 
et justifie ton analyse avec des observations. Résume par une tendance globale.

Il y a moins de 24h :
{formatter_posts(avis['il_y_a_24h'])}

Il y a moins d'une semaine :
{formatter_posts(avis['il_y_a_une_semaine'])}

Il y a moins d'un mois :
{formatter_posts(avis['il_y_a_un_mois'])}
"""

    # Fusion de tous les avis
    tous_les_avis = avis['il_y_a_24h'] + avis['il_y_a_une_semaine'] + avis['il_y_a_un_mois']

    # A. Analyse des sentiments
    sentiments = []
    times = []

    for avis_item in tous_les_avis:
        texte = avis_item.get("titre", "")
        date = avis_item.get("date")
        if texte.strip():
            polarite = TextBlob(texte).sentiment.polarity
            sentiment = "positif" if polarite > 0 else "negatif" if polarite < 0 else "neutre"
            sentiments.append(sentiment)
            times.append(date if isinstance(date, datetime) else datetime.now())
            print(f" {texte} Polarité : {polarite} {sentiment}")

    # B. Statistiques
    df = Counter(sentiments)
    total = sum(df.values())
    pos_ratio = df["positif"] / total if total else 0
    neg_ratio = df["negatif"] / total if total else 0
    neu_ratio = df["neutre"] / total if total else 0

    print(f"{df['positif']}/{total} avis positifs ({pos_ratio*100:.1f}%)")
    print(f"{df['negatif']}/{total} avis négatifs ({neg_ratio*100:.1f}%)")
    print(f"{df['neutre']}/{total} avis neutres ({neu_ratio*100:.1f}%)")

    # Pourcentages
    pos_pct = pos_ratio * 100
    neg_pct = neg_ratio * 100
    neu_pct = neu_ratio * 100

    # C. Affichage avec jauge et annotations
    fig2 = go.Figure(go.Indicator(
        mode="gauge+number",
        title={"text": f"Répartition des avis sur '{mot_cle}'"},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0, pos_pct], "color": "green"},
                {"range": [pos_pct, pos_pct + neg_pct], "color": "red"},
                {"range": [pos_pct + neg_pct, 100], "color": "gray"}
            ]
        }
    ))

    # Ajout des annotations (trick : les positions x sont approximées visuellement)
    fig2.update_layout(
        annotations=[
            dict(x=0.15, y=0.15, text=f"Positif {pos_pct:.1f}%", showarrow=False, font=dict(color="black", size=14)),
            dict(x=0.50, y=0.15, text=f"Négatif {neg_pct:.1f}%", showarrow=False, font=dict(color="black", size=14)),
            dict(x=0.85, y=0.15, text=f"Neutre {neu_pct:.1f}%", showarrow=False, font=dict(color="black", size=14))
        ]
    )

    fig2.show()

    return prompt

# Interface graphique
class RedditAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Analyseur de Sentiments Reddit")
        
        # Cadre principal
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Entrée mot-clé
        ttk.Label(main_frame, text="Mot-clé:").grid(row=0, column=0, sticky=tk.W)
        self.keyword_entry = ttk.Entry(main_frame, width=40)
        self.keyword_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.keyword_entry.insert(0, "Trump")
        
        # Limite de résultats
        ttk.Label(main_frame, text="Limite:").grid(row=1, column=0, sticky=tk.W)
        self.limit_entry = ttk.Entry(main_frame, width=10)
        self.limit_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.limit_entry.insert(0, "1000")
        
        # Bouton d'analyse
        self.analyze_btn = ttk.Button(main_frame, text="Analyser", command=self.analyze)
        self.analyze_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Onglets
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW)
        
        # Onglet Résultats
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="Résultats")
        
        # Onglet Analyse Gemini
        self.gemini_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.gemini_tab, text="Analyse Gemini")
        
        # Configuration des onglets
        self.setup_results_tab()
        self.setup_gemini_tab()
        
        # Configurer le redimensionnement
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
    def setup_results_tab(self):
        # Treeview pour afficher les résultats
        self.tree = ttk.Treeview(self.results_tab, columns=('date', 'titre', 'score', 'sentiment'), show='headings')
        
        # Configurer les colonnes
        self.tree.heading('date', text='Date')
        self.tree.heading('titre', text='Titre')
        self.tree.heading('score', text='Score')
        self.tree.heading('sentiment', text='Sentiment')
        
        self.tree.column('date', width=120)
        self.tree.column('titre', width=300)
        self.tree.column('score', width=60)
        self.tree.column('sentiment', width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.results_tab, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Placement
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_gemini_tab(self):
        # Zone de texte pour l'analyse Gemini
        self.gemini_text = scrolledtext.ScrolledText(self.gemini_tab, wrap=tk.WORD)
        self.gemini_text.pack(fill=tk.BOTH, expand=True)
        
    def analyze(self):
        keyword = self.keyword_entry.get()
        limit = int(self.limit_entry.get())
        
        if not keyword:
            messagebox.showerror("Erreur", "Veuillez entrer un mot-clé")
            return
        
        try:
            # Appel de vos fonctions existantes
            prompt = generer_prompt_pour_gemini(keyword, limit)
            response = gemini_model.generate_content(prompt)
            
            # Affichage des résultats
            self.display_results(keyword, limit)
            self.gemini_text.delete(1.0, tk.END)
            self.gemini_text.insert(tk.END, response.text)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {str(e)}")
    
    def display_results(self, keyword, limit):
        # Effacer les résultats précédents
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Récupérer les avis
        avis = chercher_avis(keyword, limit)
        tous_avis = avis['il_y_a_24h'] + avis['il_y_a_une_semaine'] + avis['il_y_a_un_mois']
        
        # Ajouter chaque avis au Treeview
        for avis in tous_avis:
            texte = avis['titre']
            polarite = TextBlob(texte).sentiment.polarity
            sentiment = "positif" if polarite > 0 else "negatif" if polarite < 0 else "neutre"
            
            self.tree.insert('', tk.END, values=(
                avis['date'],
                avis['titre'],
                avis['score'],
                sentiment
            ))

# Lancer l'application
if __name__ == "__main__":
    root = tk.Tk()
    app = RedditAnalyzerApp(root)
    root.mainloop()
