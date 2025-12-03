from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Any


class DataProvider(ABC):
    """
    Interface de provedor de dados do relatório (Repository Pattern).

    Responsável por fornecer informações de negócio de forma desacoplada
    da camada web/visual. Uma implementação concreta (ex.: PostgreSQL) poderá
    substituir a implementação mock sem alterar as camadas superiores.
    """

    @abstractmethod
    def listar_clientes(self) -> List[int]:
        """Retorna uma lista de IDs de clientes disponíveis."""
        raise NotImplementedError

    @abstractmethod
    def obter_contexto_dados(self, cliente_id: int, periodo: str) -> Dict[str, Any]:
        """
        Gera/retorna o contexto de DADOS do relatório (sem gráficos), incluindo:
        - dados básicos do cliente
        - KPIs
        - indicadores
        - tabelas (ex.: ROE vs CDI)

        Retorna um dicionário com a chave "dados" no formato esperado pelo template.
        """
        raise NotImplementedError
