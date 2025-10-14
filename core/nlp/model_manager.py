"""
Roxane OS - Model Manager
Gestion du modèle LLM (LLaMA) et génération de texte
"""

import torch
from typing import Dict, Optional, List
from dataclasses import dataclass
from loguru import logger
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


@dataclass
class GenerationConfig:
    """Configuration de génération"""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    max_tokens: int = 2048
    repetition_penalty: float = 1.1


@dataclass
class ModelResponse:
    """Réponse du modèle"""
    text: str
    tokens_used: int
    latency: float


class ModelManager:
    """
    Gestionnaire du modèle LLM
    Charge et gère LLaMA avec optimisations (quantization, LoRA)
    """
    
    def __init__(self, config: Dict):
        """
        Initialise le gestionnaire de modèle
        
        Args:
            config: Configuration du modèle
        """
        logger.info("🧠 Initializing Model Manager...")
        
        self.config = config
        self.model_name = config.get('model', {}).get('name', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0')
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Charger le modèle
        self._load_model()
        
        # LoRA adapters (si disponibles)
        self.lora_adapters = {}
        self._load_lora_adapters()
        
        logger.success(f"✅ Model loaded: {self.model_name} on {self.device}")
    
    def _load_model(self):
        """Charge le modèle LLM"""
        logger.info(f"Loading model: {self.model_name}...")
        
        # Configuration de quantization (4-bit pour économiser VRAM)
        if self.device == "cuda":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True
            )
        else:
            quantization_config = None
        
        # Charger le tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        # S'assurer qu'il y a un pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Charger le modèle
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quantization_config,
            device_map="auto" if self.device == "cuda" else None,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        # Mode evaluation
        self.model.eval()
        
        logger.info(f"Model loaded on {self.device}")
        if self.device == "cuda":
            logger.info(f"VRAM used: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    
    def _load_lora_adapters(self):
        """Charge les adaptateurs LoRA personnalisés"""
        try:
            from peft import PeftModel
            
            lora_paths = {
                'personality': '/opt/roxane/data/lora/roxane-personality-v1',
                'system': '/opt/roxane/data/lora/roxane-system-v1',
            }
            
            for name, path in lora_paths.items():
                try:
                    adapter = PeftModel.from_pretrained(self.model, path)
                    self.lora_adapters[name] = adapter
                    logger.info(f"✅ LoRA adapter loaded: {name}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not load LoRA {name}: {e}")
        
        except ImportError:
            logger.warning("⚠️  PEFT not installed, LoRA support disabled")
    
    async def generate(self,
                      prompt: str,
                      temperature: float = 0.7,
                      max_tokens: int = 2048,
                      **kwargs) -> str:
        """
        Génère une réponse à partir d'un prompt
        
        Args:
            prompt: Prompt d'entrée
            temperature: Température de génération (0-1)
            max_tokens: Nombre max de tokens
            
        Returns:
            Texte généré
        """
        import time
        start_time = time.time()
        
        # Tokenizer le prompt
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096
        ).to(self.device)
        
        # Paramètres de génération
        generation_config = {
            'max_new_tokens': max_tokens,
            'temperature': temperature,
            'top_p': kwargs.get('top_p', 0.9),
            'top_k': kwargs.get('top_k', 50),
            'repetition_penalty': kwargs.get('repetition_penalty', 1.1),
            'do_sample': True,
            'pad_token_id': self.tokenizer.pad_token_id,
            'eos_token_id': self.tokenizer.eos_token_id,
        }
        
        # Générer
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                **generation_config
            )
        
        # Décoder
        generated_text = self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        # Extraire uniquement la réponse (après le prompt)
        if prompt in generated_text:
            response = generated_text.split(prompt)[-1].strip()
        else:
            response = generated_text.strip()
        
        latency = time.time() - start_time
        logger.debug(f"Generated {len(outputs[0])} tokens in {latency:.2f}s")
        
        return response
    
    async def embed(self, text: str) -> List[float]:
        """
        Génère un embedding pour un texte
        
        Args:
            text: Texte à embedder
            
        Returns:
            Vecteur d'embedding
        """
        # Pour les embeddings, utiliser un modèle dédié
        # (à implémenter avec sentence-transformers)
        pass
    
    def get_model_info(self) -> Dict:
        """Retourne les informations sur le modèle"""
        info = {
            'name': self.model_name,
            'device': self.device,
            'dtype': str(self.model.dtype),
            'lora_adapters': list(self.lora_adapters.keys()),
        }
        
        if self.device == "cuda":
            info['vram_allocated'] = f"{torch.cuda.memory_allocated() / 1e9:.2f} GB"
            info['vram_reserved'] = f"{torch.cuda.memory_reserved() / 1e9:.2f} GB"
        
        return info
    
    async def shutdown(self):
        """Libère les ressources"""
        logger.info("🛑 Shutting down Model Manager...")
        
        # Libérer la mémoire GPU
        if self.device == "cuda":
            del self.model
            torch.cuda.empty_cache()
        
        logger.success("✅ Model Manager shut down")