"""Tests for ml_core.skills: splitting, synonym normalisation, vocabulary, extraction, SkillBinarizer."""
import numpy as np
import pytest
from sklearn.base import clone

from ml_core.skills import (
    BASE_SYNONYMS,
    SkillBinarizer,
    SkillVocab,
    compare_skills,
    extract_skills_rule_based,
    normalise_skill,
    normalise_skills,
    split_skills,
)


@pytest.fixture
def vocab():
    # Illustrative vocabulary for tests only (the real one is built from both datasets in the notebook).
    return SkillVocab.build(
        [["python", "sql", "machine learning", "excel", "javascript", "r", "c++", "c",
          "data visualization", "data analysis", "artificial intelligence", "learning"]],
        BASE_SYNONYMS,
    )


def test_split_handles_all_separators():
    assert split_skills("Python; SQL / Excel | ML, ") == ["Python", "SQL", "Excel", "ML"]


def test_split_keeps_ui_ux_together():
    # Real Internshala skill "UI/UX Design" must not split on its slash
    assert split_skills("UI/UX Design, Figma") == ["UI/UX Design", "Figma"]


def test_split_drops_placeholders():
    assert split_skills("Not Available") == []
    assert split_skills("nan") == []
    assert split_skills("") == []


def test_synonyms():
    assert normalise_skill(" JS ", BASE_SYNONYMS) == "javascript"
    assert normalise_skill("MS-Excel", BASE_SYNONYMS) == "excel"
    assert normalise_skill("ML", BASE_SYNONYMS) == "machine learning"
    assert normalise_skill("py", BASE_SYNONYMS) == "python"


def test_normalise_keeps_balanced_brackets():
    # real Internshala skills
    assert normalise_skill("English Proficiency (Spoken)", BASE_SYNONYMS) == "english proficiency (spoken)"
    assert normalise_skill("Client Relationship Management (CRM)", BASE_SYNONYMS) == "client relationship management (crm)"
    assert normalise_skill("(Python)", BASE_SYNONYMS) == "python"
    assert normalise_skill("Python)", BASE_SYNONYMS) == "python"


def test_normalise_collapses_whitespace_and_case():
    assert normalise_skill("  Machine   Learning. ", BASE_SYNONYMS) == "machine learning"


def test_normalise_unknown_skills_returns_empty(vocab):
    assert normalise_skills("Basket weaving", vocab) == []


def test_normalise_is_sorted_unique(vocab):
    assert normalise_skills("py, Python, SQL", vocab) == ["python", "sql"]


def test_normalise_accepts_list(vocab):
    assert normalise_skills(["Excel", "ms excel"], vocab) == ["excel"]


def test_compound_skill_is_split(vocab):
    # Real Student Career token: "Artificial Intelligence (AI) and Machine Learning"
    assert normalise_skills("Artificial Intelligence (AI) and Machine Learning", vocab) == [
        "artificial intelligence", "machine learning"]
    assert normalise_skills("Data Analysis andVisualization", vocab) == ["data analysis", "data visualization"]


def test_rule_based_extracts_multiword(vocab):
    found = extract_skills_rule_based("Worked on Machine Learning and SQL.", vocab)
    assert found == ["machine learning", "sql"]


def test_rule_based_longest_match_wins(vocab):
    # "learning" is in the vocab but is part of "machine learning" here
    assert "learning" not in extract_skills_rule_based("machine learning projects", vocab)


def test_rule_based_word_boundary(vocab):
    found = extract_skills_rule_based("React developer", vocab)
    assert "r" not in found and "c" not in found


def test_rule_based_symbols(vocab):
    assert extract_skills_rule_based("Strong in C++ and Excel", vocab) == ["c++", "excel"]


def test_rule_based_synonym_in_text(vocab):
    assert extract_skills_rule_based("Knows JS and ML", vocab) == ["javascript", "machine learning"]


def test_compare_skills():
    c = compare_skills(["python", "sql"], ["python", "excel"])
    assert c.matched == ["python"] and c.missing == ["excel"] and c.extra == ["sql"]


def test_vocab_build_min_count():
    v = SkillVocab.build([["python", "sql"], ["python"]], BASE_SYNONYMS, min_count=2)
    assert v.canonical == frozenset({"python"})


def test_vocab_json_roundtrip(tmp_path, vocab):
    path = tmp_path / "skills_vocab.json"
    vocab.to_json(path)
    assert SkillVocab.from_json(path) == vocab


def test_binarizer_vocab_from_train_only():
    b = SkillBinarizer(min_count=1).fit([["python"], ["sql"]])
    X = b.transform([["python", "java"]])
    assert X.tolist() == [[1, 0]]
    assert list(b.get_feature_names_out()) == ["skill__python", "skill__sql"]


def test_binarizer_min_count():
    b = SkillBinarizer(min_count=2).fit([["a"], ["a"], ["b"]])
    assert list(b.vocabulary_) == ["a"]


def test_binarizer_counts_skill_once_per_row():
    b = SkillBinarizer(min_count=2).fit([["a", "a"], ["b"]])
    assert list(b.vocabulary_) == []


def test_binarizer_is_cloneable_and_dense_int():
    b = clone(SkillBinarizer(min_count=3))
    assert b.min_count == 3
    X = SkillBinarizer(min_count=1).fit([["x"]]).transform([["x"], []])
    assert X.dtype == np.int8 and X.tolist() == [[1], [0]]


# --- D-022: survey spelling variants collapse to one canonical skill ----------------------------
@pytest.mark.parametrize("raw,canonical", [
    ("Interpersonnal Skills", "interpersonal skills"),
    ("interpersonalskills", "interpersonal skills"),
    ("cybersec", "cybersecurity"),
    ("Android App Make", "android app development"),
    ("android application develop", "android app development"),
    ("Database Developement", "database development"),
    ("Web Based Projectdevelop", "web development"),
    ("Cryptograph", "cryptography"),
    ("Data Scientist", "data science"),
    ("Statisticians", "statistics"),
    ("Robotics Knowhow", "robotics knowledge"),
    ("Problemsolving & Analyzing", "problem solving"),
    ("UX/UI Knowledge", "ui/ux design"),
    ("iot", "internet of things"),
    # Phase 6.5: near-duplicates still left in the 215-skill model vocabulary
    ("adaptibility", "adaptability"),
    ("API Tester", "api testing"), ("apitesting", "api testing"),
    ("Android", "android app development"), ("Android Apps Develop", "android app development"),
    ("Mobile Application Develop", "mobile app development"),
    ("Big Data Technations", "big data technologies"), ("Big", "big data technologies"),
    ("Data Technologies", "big data technologies"),
    ("Data Enginer", "data engineering"), ("Data Scienc", "data science"),
    ("DatabaseDevelopment", "database development"),
    ("WebDevelopment", "web development"), ("Website Development", "web development"),
    ("Website Building", "web development"),
    ("Web based project developed", "web development"), ("Web BasedProject Developing", "web development"),
    ("WebBasedProject Develop", "web development"),
    ("deeplearning.net", "deep learning"),
    ("Graphic Design & Editing", "graphic design"), ("Graphic Design and Editing", "graphic design"),
    ("Network Securities", "network security"),
    ("Operating System and Networking", "operating systems and networking"),
    ("Problemsolving and Analytical", "problem solving"),
    ("Video Editing and Annotation", "video editing"), ("Digital Art and Design", "digital art"),
])
def test_survey_variants_collapse(raw, canonical):
    assert normalise_skill(raw, BASE_SYNONYMS) == canonical


def test_glued_survey_compounds_split():
    v = SkillVocab.build([["artificial intelligence", "machine learning", "operating systems and networking",
                           "big data technologies"]], BASE_SYNONYMS)
    assert normalise_skills("Artificial Intelligence (AI) andMachine Learning", v) == [
        "artificial intelligence", "machine learning"]
    assert normalise_skills("Operating Systems and Networking Big Data Technologies", v) == [
        "big data technologies", "operating systems and networking"]


def test_survey_compound_splits():
    v = SkillVocab.build([["problem solving", "communication", "video editing", "animation",
                           "artificial intelligence", "machine learning", "game development"]], BASE_SYNONYMS)
    assert normalise_skills("Problem Solving and Communication", v) == ["communication", "problem solving"]
    assert normalise_skills("Video Editing & Animation", v) == ["animation", "video editing"]
    assert normalise_skills("Artifical Intelligence (AI) and Machine Learning", v) == [
        "artificial intelligence", "machine learning"]
    assert normalise_skills("game develop} artificial intelligence (ai) and machine learning", v) == [
        "artificial intelligence", "game development", "machine learning"]
