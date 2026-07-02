# -*- coding: utf-8 -*-

class AuditoriaContext:
    def __init__(self):
        # Declaração explícita de todos os atributos
        self.dados_atos = None
        self.dados_selos = None
        self.resultado_auditoria = None
        self.status = "iniciado"

    def resetar(self):
        """Limpa o contexto resetando os valores para o estado inicial."""
        self.dados_atos = None
        self.dados_selos = None
        self.resultado_auditoria = None
        self.status = "iniciado"

# Instancia o objeto global
context = AuditoriaContext()