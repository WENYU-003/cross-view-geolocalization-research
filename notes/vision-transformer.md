# Vision Transformer Notes

## High-Level Pipeline
```text
Image
  ↓
Patch Embedding
  ↓
Patch Tokens
  ↓
Class Token + Position Embedding
  ↓
Transformer Encoder Blocks × L
  ↓
Feature Representation
  ↓
Task Head
```

## Patch Embedding
For ViT-B/16 with a 224×224 RGB image:
- Patch size: 16×16
- Grid: 14×14
- Number of patches: 196
- Embedding dimension: 768

Typical tensor flow:

```text
[B, 3, 224, 224]
      ↓ Conv2d(kernel=16, stride=16, out_channels=768)
[B, 768, 14, 14]
      ↓ flatten + transpose
[B, 196, 768]
```

A learnable class token can then be concatenated:

```text
[B, 196, 768] → [B, 197, 768]
```

Position embeddings are **added**, not concatenated, so the shape remains `[B, 197, 768]`.

## Self-Attention
Q, K, and V are generated from the same input token sequence.

```text
Q = XWq
K = XWk
V = XWv
Attention(Q,K,V) = softmax(QKᵀ / √d) V
```

## Multi-Head Attention
The embedding dimension is divided across multiple heads. Each head learns attention in a different subspace; the head outputs are concatenated and projected back to the original embedding dimension.

For `dim=768` and `num_heads=12`:
- each head dimension = 64
- total dimension after concatenation = 768

## Transformer Encoder Block
A ViT encoder block contains:
1. LayerNorm
2. Multi-Head Self-Attention
3. Residual connection
4. LayerNorm
5. MLP / FFN
6. Residual connection

The block is repeated `L` times.

## MLP / FFN
For ViT-B/16, a common expansion is:

```text
768 → 3072 → 768
```

The expansion gives each token a larger nonlinear feature transformation space before returning to the model dimension.

## Other Concepts Studied
- GELU
- Dropout
- DropPath / stochastic depth
- Residual connections
- LayerNorm
- QKV linear projection
- tensor reshape / permute / transpose
