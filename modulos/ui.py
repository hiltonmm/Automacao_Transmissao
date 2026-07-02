# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

def obter_data_interface():
    """Gerencia a interface de captura e validação de data."""
    resultado_data = []

    def formatar_data(event):
        if event.keysym == "BackSpace":
            return
        texto = entry_data.get().replace("/", "")[:8]
        novo_texto = ""
        for i, char in enumerate(texto):
            if char.isdigit():
                if i in [2, 4]: novo_texto += "/"
                novo_texto += char
        entry_data.delete(0, tk.END)
        entry_data.insert(0, novo_texto)

    def validar_e_salvar(event=None):
        data_digitada = entry_data.get()
        try:
            datetime.strptime(data_digitada, "%d/%m/%Y")
            resultado_data.append(data_digitada.replace("/", ""))
            root.destroy()
        except ValueError:
            messagebox.showerror("Data Inválida", "Por favor, digite uma data válida no formato DD/MM/AAAA.")
            entry_data.delete(0, tk.END)

    def cancelar_operacao():
        root.destroy()

    root = tk.Tk()
    root.title("Configuração do Robô")
    root.geometry("320x160")
    # Centralização forçada
    root.eval('tk::PlaceWindow . center')
    root.attributes("-topmost", True)
    root.protocol("WM_DELETE_WINDOW", cancelar_operacao)

    root.bind('<Return>', validar_e_salvar)

    tk.Label(root, text="Informe a data para gerar os relatórios:", font=("Arial", 10)).pack(pady=15)
    entry_data = tk.Entry(root, font=("Arial", 14), justify="center", width=12)
    entry_data.pack(pady=5)
    entry_data.bind("<KeyRelease>", formatar_data)

    btn_iniciar = tk.Button(root, text="Iniciar Automação", command=validar_e_salvar, bg="#4CAF50", fg="white",
                            font=("Arial", 10, "bold"))
    btn_iniciar.pack(pady=10)

    entry_data.focus()
    root.mainloop()

    if not resultado_data:
        raise RuntimeError("Operação cancelada pelo usuário.")
    return resultado_data[0]