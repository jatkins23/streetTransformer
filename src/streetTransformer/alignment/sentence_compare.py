from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np

# Load CLIP text encoder
model = SentenceTransformer("clip-ViT-B-32")

def compare_sentence_pairs(sents1, sents2, references=None, return_refclip=True) -> dict:
    """
    Compare two lists of sentences using CLIP.
    Returns a tensor of cosine similarities (one per pair).
    """
    assert len(sents1) == len(sents2), "Both lists must have same length"
    
    # Encode all sentences at once
    emb1 = model.encode(sents1, convert_to_tensor=True, normalize_embeddings=True)
    emb2 = model.encode(sents2, convert_to_tensor=True, normalize_embeddings=True)

    # Cosine similarity for each pair (vectorized)
    sims = torch.sum(emb1 * emb2, dim=1)   # normalized => dot = cosine
    sims = sims.clamp(min=0)               # CLIPScore convention
    sims_np = sims.cpu().numpy()

    if return_refclip:
        refclip_scores = []
        for i in range(len(sents1)):
            cand_emb = emb1[i].unsqueeze(0)
            img_emb  = emb2[i].unsqueeze(0)  # treat sents2 as "image side" analogue

            # image-candidate score
            s_ic = torch.sum(cand_emb * img_emb).clamp(min=0).item()

            # references: either provided or fallback to sents2
            if references is not None and references[i]:
                ref_embs = model.encode(references[i], convert_to_tensor=True, normalize_embeddings=True)
            else:
                ref_embs = emb2[i].unsqueeze(0)

            s_tr = torch.max(torch.sum(cand_emb * ref_embs, dim=1)).clamp(min=0).item()

            # harmonic mean
            eps = 1e-8
            refclip = 2 * s_ic * s_tr / (s_ic + s_tr + eps)
            refclip_scores.append(refclip)

    metrics = {
        'cosine_similarity_scores': sims_np,
        'refclip_scores': np.array(refclip_scores) if return_refclip else np.zeros(len(sims_np))
    }
    return metrics

# Example
# sents1 = ["A dog running in a park", "A close-up of a pizza"]
# sents2 = ["A puppy playing outside", "A picture of pasta"]

# print(compare_sentence_pairs(sents1, sents2))
