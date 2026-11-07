"""AI assistance layer (scikit-learn). The AI only SUGGESTS: routing, priority, summary and
duplicates. A human official always confirms or overrides - nothing is decided automatically."""
import re
from collections import Counter

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import make_pipeline

from data.training_data import TRAINING

DEPARTMENTS = sorted(TRAINING.keys()) + ["Administration"]
LOW_CONFIDENCE = 0.28

HIGH_WORDS = ["urgent", "emergency", "immediately", "fire", "unsafe", "danger", "harass", "ragging",
              "assault", "threat", "injur", "medical", "faint", "shock", "short circuit",
              "gas leak", "suicid", "bully", "abuse", "molest", "accident"]
SENSITIVE_WORDS = ["harass", "ragging", "assault", "abuse", "bully", "discriminat", "threat",
                   "depress", "suicid", "molest", "counsel", "mental"]
MEDIUM_WORDS = ["not working", "broken", "delay", "leak", "dirty", "unhygienic", "fail", "missing",
                "wrong", "error", "pending", "cannot", "can't", "unable", "late", "not responding",
                "poor", "slow", "clash"]

_texts, _labels = [], []
for _dept, _examples in TRAINING.items():
    for _e in _examples:
        _texts.append(_e)
        _labels.append(_dept)

_model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True),
    LogisticRegression(C=20, max_iter=1000),
)
_model.fit(_texts, _labels)


def classify(text):
    """Return (department, confidence). Low confidence -> 'Administration' for human routing."""
    probs = _model.predict_proba([text])[0]
    best = probs.argmax()
    dept, conf = _model.classes_[best], float(probs[best])
    if conf < LOW_CONFIDENCE:
        return "Administration", conf
    return dept, conf


def prioritize(text):
    """Rule-based priority plus a sensitive-case flag. Returns (priority, sensitive)."""
    t = text.lower()
    sensitive = any(w in t for w in SENSITIVE_WORDS)
    if sensitive or any(w in t for w in HIGH_WORDS):
        return "high", sensitive
    if any(w in t for w in MEDIUM_WORDS):
        return "medium", False
    return "low", False


def summarize(text, limit=200):
    """Extractive summary: choose the most informative sentence."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return ""
    if len(sentences) > 1:
        words = [w for w in re.findall(r"[a-z']+", text.lower()) if w not in ENGLISH_STOP_WORDS]
        freq = Counter(words)

        def score(s):
            toks = [w for w in re.findall(r"[a-z']+", s.lower()) if w not in ENGLISH_STOP_WORDS]
            return sum(freq[w] for w in toks) / (len(toks) ** 0.5 or 1)

        best = max(sentences, key=score)
    else:
        best = sentences[0]
    return best if len(best) <= limit else best[: limit - 3].rstrip() + "..."


def analyze(text):
    dept, conf = classify(text)
    priority, sensitive = prioritize(text)
    return {
        "department": dept,
        "confidence": round(conf, 2),
        "priority": priority,
        "sensitive": sensitive,
        "low_confidence": dept == "Administration",
        "summary": summarize(text),
    }


def find_duplicates(text, candidates, threshold=0.45, top=3):
    """candidates: list of (id, title, description). Returns ids of similar issues with scores."""
    if not candidates:
        return []
    corpus = [f"{t} {d}" for _, t, d in candidates]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit(corpus + [text])
    sims = cosine_similarity(vec.transform([text]), vec.transform(corpus))[0]
    ranked = sorted(zip(candidates, sims), key=lambda x: -x[1])
    return [{"id": c[0], "title": c[1], "score": round(float(s), 2)}
            for c, s in ranked[:top] if s >= threshold]
