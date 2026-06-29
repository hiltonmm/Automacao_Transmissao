class AuditoriaContext:
    def __init__(self):
        self.dados_atos = None
        self.dados_selos = None
        self.resultado_auditoria = None
        self.status = "iniciado"

context = AuditoriaContext()