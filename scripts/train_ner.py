import spacy
from spacy.tokens import DocBin
from spacy.training import Example

# Dummy training data for NER
TRAIN_DATA = [
    ("Experienced Python developer with Django and SQL.", {"entities": [(12, 18, "SKILL"), (33, 39, "SKILL"), (44, 47, "SKILL")]}),
    ("Data scientist skilled in Pandas, Machine Learning, and Python.", {"entities": [(26, 32, "SKILL"), (34, 50, "SKILL"), (56, 62, "SKILL")]}),
]

def train_spacy_ner(model=None, output_dir="models/ner_model", n_iter=10):
    if model is not None:
        nlp = spacy.load(model)
    else:
        nlp = spacy.blank("en")

    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")

    for _, annotations in TRAIN_DATA:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])

    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()
        for itn in range(n_iter):
            losses = {}
            for text, annotations in TRAIN_DATA:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                nlp.update([example], drop=0.5, sgd=optimizer, losses=losses)
            print(f"Iteration {itn} Losses: {losses}")

    nlp.to_disk(output_dir)
    print(f"Saved model to {output_dir}")

if __name__ == "__main__":
    train_spacy_ner()
