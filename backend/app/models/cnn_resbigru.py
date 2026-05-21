"""Копия архитектуры CNN-ResBiGRU для inference в backend."""

from __future__ import annotations

import torch
from torch import nn


class ResidualBiGRUBlock(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, dropout: float = 0.2) -> None:
        super().__init__()
        self.bigru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True,
        )
        self.norm = nn.LayerNorm(hidden_dim * 2)
        self.dropout = nn.Dropout(dropout)
        self.proj = nn.Linear(input_dim, hidden_dim * 2) if input_dim != hidden_dim * 2 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.proj(x)
        out, _ = self.bigru(x)
        out = self.dropout(self.norm(out))
        return out + residual


class CnnResBiGRU(nn.Module):
    def __init__(
        self,
        in_features: int,
        num_classes: int,
        conv_channels: int = 64,
        gru_hidden: int = 64,
    ) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(in_channels=in_features, out_channels=conv_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(conv_channels),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),
            nn.Dropout(0.2),
        )
        self.res_bigru = ResidualBiGRUBlock(input_dim=conv_channels, hidden_dim=gru_hidden)
        self.head = nn.Sequential(
            nn.Linear(gru_hidden * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = self.conv(x)
        x = x.transpose(1, 2)
        x = self.res_bigru(x)
        x = x[:, -1, :]
        return self.head(x)
