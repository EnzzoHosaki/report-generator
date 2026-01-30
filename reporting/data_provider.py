from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class DataProvider(ABC):
    """
    Interface de provedor de dados do relatório (Repository Pattern).
    """

    @abstractmethod
    def listar_clientes(self) -> List[Dict[str, Any]]:
        """Retorna uma lista de clientes disponíveis."""
        raise NotImplementedError

    @abstractmethod
    def listar_filiais(self, cliente_id: int) -> List[Dict[str, Any]]:
        """Retorna lista de filiais de um cliente."""
        raise NotImplementedError

    @abstractmethod
    def obter_contexto_dados(
        self, 
        cliente_id: int, 
        anos: List[int], 
        meses: List[int], 
        filiais: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Gera/retorna o contexto de DADOS do relatório.
        """
        raise NotImplementedError