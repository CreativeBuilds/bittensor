from typing import Optional

import torch.nn as nn
from transformers import AutoConfig, AutoModel
from ..base import Critic


class AutoCritic(Critic):
    """
    Auto Critic model.

    Args:
        pretrained (str): Pretrained model name or path.
        config (AutoConfig): Model config.
        checkpoint (bool): Enable gradient checkpointing.
        lora_rank (int): Rank of the low-rank approximation.
        lora_train_bias (str): LoRA bias training mode.
    """

    def __init__(
        self,
        pretrained: Optional[str] = None,
        config: Optional[AutoConfig] = None,
        checkpoint: bool = False,
        lora_rank: int = 0,
        lora_train_bias: str = "none",
        **kwargs
    ) -> None:
        if pretrained is not None:
            model = AutoModel.from_pretrained(pretrained)
        elif config is not None:
            model = AutoModel(config)
        else:
            model = AutoModel(AutoConfig())
        if checkpoint:
            model.gradient_checkpointing_enable()
        value_head = nn.Linear(model.config.word_embed_proj_dim, 1)
        super().__init__(model, value_head, lora_rank, lora_train_bias, **kwargs)
