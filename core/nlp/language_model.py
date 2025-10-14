"""
Roxane OS - Language Model Implementation
Implémentation concrète de ILanguageModel avec LLaMA
"""

import torch
import time
import numpy as np
from typing import List, Dict, Any
from loguru import logger
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from sentence_transformers import SentenceTransformer

from core.interfaces import ILanguageModel, ModelResponse, ModelException


class LLaMAModel(ILanguageModel):
    """
    Implémentation de ILanguageModel avec LLaMA
    
    Single Responsibility: Gère uniquement l'inférence du modèle LLaMA
    """
    
    def __init__(
        self,
        model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        device: str = "auto",
        quantization: str = "4bit",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialise le modèle LLaMA
        
        Args:
            model_name: Nom du modèle HuggingFace
            device: Device (auto, cuda, cpu)
            quantization: Type de quantization (none, 4bit, 8bit)
            embedding_model: Modèle pour les embeddings
        """
        self._model_name = model_name
        self._device = self._resolve_device(device)
        self._quantization = quantization
        self._embedding_model_name = embedding_model
        
        logger.info(f"Loading LLaMA model: {model_name}")
        self._load_model()
        
        logger.info(f"Loading embedding model: {embedding_model}")
        self._load_embedding_model()
        
        logger.success(f"✅ Model loaded on {self._device}")
    
    def _load_embedding_model(self) -> None:
        """Charge le modèle d'embedding"""
        try:
            self._embedding_model = SentenceTransformer(
                self._embedding_model_name,
                device=self._device
            )
            logger.success(f"✅ Embedding model loaded: {self._embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._embedding_model = None
    
    def _resolve_device(self, device: str) -> str:
        """Résout le device à utiliser"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _load_model(self) -> None:
        """Charge le modèle et le tokenizer"""
        try:
            # Configuration de quantization
            quant_config = None
            if self._quantization == "4bit" and self._device == "cuda":
                quant_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
            
            # Charger le tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_name,
                trust_remote_code=True
            )
            
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Charger le modèle
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_name,
                quantization_config=quant_config,
                device_map="auto" if self._device == "cuda" else None,
                torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self._model.eval()
            
            if self._device == "cuda":
                vram_gb = torch.cuda.memory_allocated() / 1e9
                logger.info(f"VRAM allocated: {vram_gb:.2f} GB")
                
        except Exception as e:
            raise ModelException(f"Failed to load model: {str(e)}") from e
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> ModelResponse:
        """
        Génère une réponse à partir d'un prompt
        
        Args:
            prompt: Prompt d'entrée
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température de sampling
            **kwargs: Paramètres additionnels
            
        Returns:
            ModelResponse avec la réponse générée
            
        Raises:
            ModelException: En cas d'erreur de génération
        """
        start_time = time.time()
        
        try:
            # Tokeniser
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=4096
            ).to(self._device)
            
            # Paramètres de génération
            generation_config = {
                'max_new_tokens': max_tokens,
                'temperature': temperature,
                'top_p': kwargs.get('top_p', 0.9),
                'top_k': kwargs.get('top_k', 50),
                'repetition_penalty': kwargs.get('repetition_penalty', 1.1),
                'do_sample': True,
                'pad_token_id': self._tokenizer.pad_token_id,
                'eos_token_id': self._tokenizer.eos_token_id,
            }
            
            # Générer
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    **generation_config
                )
            
            # Décoder
            generated_text = self._tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )
            
            # Extraire uniquement la réponse (après le prompt)
            response_text = self._extract_response(generated_text, prompt)
            
            latency = time.time() - start_time
            tokens_used = len(outputs[0])
            
            logger.debug(f"Generated {tokens_used} tokens in {latency:.2f}s")
            
            # Calculer la confidence basée sur la longueur et la cohérence
            confidence = self._calculate_confidence(response_text, prompt)
            
            return ModelResponse(
                text=response_text,
                confidence=confidence,
                tokens_used=tokens_used,
                latency=latency
            )
            
        except Exception as e:
            raise ModelException(f"Generation failed: {str(e)}") from e
    
    def _extract_response(self, generated: str, prompt: str) -> str:
        """Extrait la réponse du texte généré"""
        if prompt in generated:
            return generated.split(prompt)[-1].strip()
        return generated.strip()
    
    def _calculate_confidence(self, response: str, prompt: str) -> float:
        """
        Calcule la confidence de la réponse générée
        
        Args:
            response: Réponse générée
            prompt: Prompt original
            
        Returns:
            Score de confidence entre 0 et 1
        """
        try:
            confidence_factors = []
            
            # 1. Longueur de la réponse (ni trop courte, ni trop longue)
            response_length = len(response.split())
            if response_length < 3:
                confidence_factors.append(0.3)  # Trop court
            elif response_length > 200:
                confidence_factors.append(0.7)  # Trop long
            else:
                confidence_factors.append(0.9)  # Longueur appropriée
            
            # 2. Cohérence (pas de répétitions excessives)
            words = response.lower().split()
            if len(words) > 0:
                unique_words = len(set(words))
                repetition_ratio = unique_words / len(words)
                confidence_factors.append(repetition_ratio)
            else:
                confidence_factors.append(0.1)
            
            # 3. Présence de mots-clés pertinents
            relevant_keywords = ['oui', 'non', 'merci', 'bonjour', 'au revoir', 'comment', 'pourquoi', 'quand', 'où']
            keyword_count = sum(1 for word in words if word in relevant_keywords)
            keyword_score = min(1.0, keyword_count / 3)  # Normaliser
            confidence_factors.append(keyword_score)
            
            # 4. Absence de caractères bizarres
            weird_chars = ['�', '�', '�', '�', '�']
            weird_count = sum(response.count(char) for char in weird_chars)
            weird_score = max(0.1, 1.0 - (weird_count / len(response)))
            confidence_factors.append(weird_score)
            
            # Calculer la moyenne pondérée
            weights = [0.3, 0.3, 0.2, 0.2]  # Poids pour chaque facteur
            weighted_confidence = sum(factor * weight for factor, weight in zip(confidence_factors, weights))
            
            # Clamp entre 0.1 et 0.95
            return max(0.1, min(0.95, weighted_confidence))
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.5  # Valeur par défaut
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding pour un texte
        
        Args:
            text: Texte à encoder
            
        Returns:
            Liste des valeurs d'embedding
            
        Raises:
            ModelException: Si le modèle d'embedding n'est pas disponible
        """
        if self._embedding_model is None:
            raise ModelException("Embedding model not loaded")
        
        try:
            # Générer l'embedding
            embedding = self._embedding_model.encode(text)
            
            # Convertir en liste Python
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise ModelException(f"Embedding generation failed: {e}")
    
    async def similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité cosinus entre deux textes
        
        Args:
            text1: Premier texte
            text2: Deuxième texte
            
        Returns:
            Score de similarité entre 0 et 1
        """
        try:
            # Générer les embeddings
            embedding1 = await self.get_embedding(text1)
            embedding2 = await self.get_embedding(text2)
            
            # Calculer la similarité cosinus
            similarity = self._cosine_similarity(embedding1, embedding2)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calcule la similarité cosinus entre deux vecteurs"""
        try:
            # Convertir en numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculer la similarité cosinus
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            
            # Clamp entre 0 et 1
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le modèle"""
        info = {
            'name': self._model_name,
            'device': self._device,
            'quantization': self._quantization,
            'dtype': str(self._model.dtype) if hasattr(self._model, 'dtype') else 'unknown',
        }
        
        if self._device == "cuda":
            info['vram_allocated'] = f"{torch.cuda.memory_allocated() / 1e9:.2f} GB"
            info['vram_reserved'] = f"{torch.cuda.memory_reserved() / 1e9:.2f} GB"
        
        return info
    
    def __del__(self):
        """Nettoyage lors de la destruction"""
        if hasattr(self, '_model') and self._device == "cuda":
            del self._model
            torch.cuda.empty_cache()