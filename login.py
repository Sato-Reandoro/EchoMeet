import tkinter as tk
from tkinter import messagebox

# Dicionário para armazenar os usuários
usuarios_validos = {
    "usuario1": "senha1",
    "usuario2": "senha2"
}

# Função para verificar o login
def verificar_login():
    usuario = entrada_usuario.get()
    senha = entrada_senha.get()
    
    if usuario in usuarios_validos and usuarios_validos[usuario] == senha:
        messagebox.showinfo("Login", "Login bem-sucedido!")
    else:
        messagebox.showerror("Login", "Usuário ou senha incorretos.")

# Função para abrir a janela de registro de novo usuário
def nova_janela_usuario():
    nova_janela = tk.Toplevel()
    nova_janela.title("Criar Novo Usuário")
    nova_janela.geometry("300x200")
    
    # Rótulo e entrada para o novo usuário
    rotulo_novo_usuario = tk.Label(nova_janela, text="Novo Usuário:")
    rotulo_novo_usuario.pack(pady=10)
    
    entrada_novo_usuario = tk.Entry(nova_janela)
    entrada_novo_usuario.pack()

    # Rótulo e entrada para a nova senha
    rotulo_nova_senha = tk.Label(nova_janela, text="Nova Senha:")
    rotulo_nova_senha.pack(pady=10)

    entrada_nova_senha = tk.Entry(nova_janela, show="*")
    entrada_nova_senha.pack()

    # Função para adicionar o novo usuário
    def registrar_usuario():
        novo_usuario = entrada_novo_usuario.get()
        nova_senha = entrada_nova_senha.get()

        if novo_usuario in usuarios_validos:
            messagebox.showerror("Erro", "Usuário já existe!")
        elif novo_usuario == "" or nova_senha == "":
            messagebox.showerror("Erro", "Usuário e senha não podem estar vazios!")
        else:
            usuarios_validos[novo_usuario] = nova_senha
            messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")
            nova_janela.destroy()  # Fecha a janela de registro

    # Botão para confirmar o registro do novo usuário
    botao_registrar = tk.Button(nova_janela, text="Registrar", command=registrar_usuario)
    botao_registrar.pack(pady=20)

# Criar a janela principal
janela = tk.Tk()
janela.title("Tela de Login")
janela.geometry("300x250")  # Largura x Altura

# Rótulo e entrada para o usuário
rotulo_usuario = tk.Label(janela, text="Usuário:")
rotulo_usuario.pack(pady=10)

entrada_usuario = tk.Entry(janela)
entrada_usuario.pack()

# Rótulo e entrada para a senha
rotulo_senha = tk.Label(janela, text="Senha:")
rotulo_senha.pack(pady=10)

entrada_senha = tk.Entry(janela, show="*")
entrada_senha.pack()

# Botão de login
botao_login = tk.Button(janela, text="Login", command=verificar_login)
botao_login.pack(pady=10)

# Botão para criar novo usuário
botao_novo_usuario = tk.Button(janela, text="Novo Usuário", command=nova_janela_usuario)
botao_novo_usuario.pack(pady=10)

# Executar a janela
janela.mainloop()
