
from flask import Flask, render_template, redirect, url_for, request, session
from flask import jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'app.db')



# Função para conectar ao banco
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    nome = session.get('usuario')
    usuario = None
    if nome:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
        usuario = cursor.fetchone()
        conn.close()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cursos LIMIT 6')
    cursos_destaque = cursor.fetchall()
    conn.close()
    return render_template('index.html', usuario=usuario, cursos_destaque=cursos_destaque)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO usuarios (nome, email) VALUES (?, ?)', (nome, email))
        conn.commit()
        # Buscar o id do usuário recém-criado
        cursor.execute('SELECT id FROM usuarios WHERE nome = ? AND email = ?', (nome, email))
        user = cursor.fetchone()
        if user:
            user_id = user['id']
            user_dir = os.path.join('static', 'images', 'usuarios', str(user_id), 'imagens')
            os.makedirs(user_dir, exist_ok=True)
        conn.close()
        return redirect(url_for('index'))
    nome = session.get('usuario')
    usuario = None
    if nome:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
        usuario = cursor.fetchone()
        conn.close()
    return render_template('cadastro.html', usuario=usuario)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ?', (email,))
        usuario = cursor.fetchone()
        conn.close()
        if usuario:
            session['usuario'] = usuario['nome']
            return redirect(url_for('index'))
    nome = session.get('usuario')
    usuario = None
    if nome:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
        usuario = cursor.fetchone()
        conn.close()
    return render_template('login.html', usuario=usuario)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

@app.route('/cursos')
def cursos():
    nome = session.get('usuario')
    usuario = None
    cursos_assistindo = []
    if nome:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
        usuario = cursor.fetchone()
        if usuario:
            cursor.execute('''
                SELECT c.* , p.progresso, p.ultima_atividade
                FROM progresso_usuario p
                JOIN cursos c ON c.id = p.curso_id
                WHERE p.usuario_id = ?
                ORDER BY p.ultima_atividade DESC
                LIMIT 4
            ''', (usuario['id'],))
            cursos_assistindo = cursor.fetchall()
        conn.close()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cursos')
    cursos = cursor.fetchall()
    conn.close()
    return render_template('cursos.html', usuario=usuario, cursos=cursos, cursos_assistindo=cursos_assistindo)

from werkzeug.utils import secure_filename
import uuid

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    nome = session.get('usuario')
    if not nome:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    if request.method == 'POST' and usuario:
        novo_nome = request.form.get('nome', usuario['nome'])
        novo_email = request.form.get('email', usuario['email'])
        nova_senha = request.form.get('senha')
        foto = request.files.get('foto')
        foto_path = usuario['foto'] if 'foto' in usuario.keys() else None
        if foto and foto.filename:
            user_id = usuario['id']
            user_dir = os.path.join('static', 'images', 'usuarios', str(user_id))
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            filename = secure_filename(f"{uuid.uuid4().hex}_{foto.filename}")
            foto_path = os.path.join(user_dir, filename).replace('\\', '/')
            foto.save(foto_path)
        if nova_senha:
            cursor.execute('UPDATE usuarios SET nome=?, email=?, senha=?, foto=? WHERE id=?',
                           (novo_nome, novo_email, nova_senha, foto_path, usuario['id']))
        else:
            cursor.execute('UPDATE usuarios SET nome=?, email=?, foto=? WHERE id=?',
                           (novo_nome, novo_email, foto_path, usuario['id']))
        conn.commit()
        # Atualiza sessão se nome mudou
        session['usuario'] = novo_nome
        # Atualiza dados do usuário
        cursor.execute('SELECT * FROM usuarios WHERE id = ?', (usuario['id'],))
        usuario = cursor.fetchone()
    cursos_assistindo = []
    if usuario:
        cursor.execute('''
            SELECT c.* , p.progresso, p.ultima_atividade
            FROM progresso_usuario p
            JOIN cursos c ON c.id = p.curso_id
            WHERE p.usuario_id = ?
            ORDER BY p.ultima_atividade DESC
            LIMIT 4
        ''', (usuario['id'],))
        cursos_assistindo = cursor.fetchall()
    conn.close()
    if not usuario:
        return redirect(url_for('login'))
    return render_template('perfil.html', usuario=usuario, cursos_assistindo=cursos_assistindo)

@app.route('/api/buscar_cursos')
def buscar_cursos():
    termo = request.args.get('q', '').strip()
    conn = get_db()
    cursor = conn.cursor()
    if termo:
        cursor.execute("SELECT * FROM cursos WHERE titulo LIKE ? OR descricao LIKE ?", (f'%{termo}%', f'%{termo}%'))
    else:
        cursor.execute("SELECT * FROM cursos")
    cursos = cursor.fetchall()
    conn.close()
    cursos_list = [
        {
            'id': c['id'],
            'titulo': c['titulo'],
            'descricao': c['descricao'],
            'capa': c['capa'],
            'instrutor': c['instrutor'] if 'instrutor' in c.keys() else '',
            'duracao': c['duracao'] if 'duracao' in c.keys() else '',
            'nivel': c['nivel'] if 'nivel' in c.keys() else '',
            'categoria': c['categoria'] if 'categoria' in c.keys() else '',
            'publicado': c['publicado'] if 'publicado' in c.keys() else '',
        } for c in cursos
    ]
    return jsonify({'cursos': cursos_list})

@app.route('/curso/<int:curso_id>')
def player_curso(curso_id):
    nome = session.get('usuario')
    usuario = None
    if nome:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
        usuario = cursor.fetchone()
        conn.close()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cursos WHERE id = ?', (curso_id,))
    curso = cursor.fetchone()
    conn.close()
    if not curso:
        return redirect(url_for('cursos'))
    return render_template('player.html', usuario=usuario, curso=curso)

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    mensagem = None
    if request.method == 'POST':
        email = request.form['email']
        # implementar o envio de e-mail real
        mensagem = f"Se o e-mail {email} estiver cadastrado, enviaremos instruções para redefinir a senha."
    return render_template('recuperar_senha.html', mensagem=mensagem)

@app.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    nome = session.get('usuario')
    usuario = None
    if nome:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
        usuario = cursor.fetchone()
        conn.close()
    # Aqui você pode adicionar lógica para atualizar dados se for POST
    return render_template('configuracoes.html', usuario=usuario)

@app.route('/admin')
def pagina_administrador():
    nome = session.get('usuario')
    if not nome:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    conn.close()
    if not usuario or usuario['email'] != 'edersonluan@exemplo.com':
        return redirect(url_for('index'))
    return render_template('pagina_administrador.html', usuario=usuario)

@app.route('/admin/painel/usuarios')
def admin_painel_usuarios():
    nome = session.get('usuario')
    if not nome:
        return '', 403
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    if not usuario or usuario['email'] != 'edersonluan@exemplo.com':
        conn.close()
        return '', 403
    cursor.execute('SELECT id, nome, email, tag FROM usuarios ORDER BY id')
    usuarios = cursor.fetchall()
    conn.close()
    html = '<h2 style="color:#fff;">Usuários cadastrados</h2>'
    html += '<table style="width:100%;border-collapse:collapse;margin-top:18px;">'
    html += '<tr style="background:#f0b41b;color:#1a2a3f;font-weight:800;"><th style="padding:8px;">ID</th><th style="padding:8px;">Nome</th><th style="padding:8px;">E-mail</th><th style="padding:8px;text-align:center;">Tag</th><th style="padding:8px;">Ações</th></tr>'
    for u in usuarios:
        tag_html = f'<span style="background:#c41d2b;color:#ffff;padding:3px 12px;border-radius:12px;font-size:0.95em;font-weight:700;display:inline-flex;align-items:center;justify-content:center;vertical-align:middle;">{u[3]}</span>' if u[3] else '-'
        html += f'<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">{u[0]}</td><td style="padding:8px;">{u[1]}</td><td style="padding:8px;">{u[2]}</td><td style="padding:8px;text-align:center;">{tag_html}</td>'
        html += f'<td style="padding:8px; text-align:center;"><button class="btn-excluir-usuario" data-id="{u[0]}" style="background:#e53935; border:none; border-radius:6px; padding:6px 10px; cursor:pointer; display:inline-flex; align-items:center; justify-content:center;"><img src=\"/static/images/lixeira_branca.svg\" alt=\"Excluir\" style=\"width:18px;height:18px;\"></button></td></tr>'
    html += '</table>'
    html += '''<style>
    .notificacao-card {
        position: fixed;
        top: 90px;
        right: 30px;
        background: #1a2a3f;
        color: #fff;
        padding: 18px 32px;
        border-radius: 10px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.18);
        font-size: 1.1em;
        z-index: 9999;
        display: none;
        align-items: center;
        gap: 10px;
        min-width: 220px;
        max-width: 90vw;
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    <div id="notificacao-excluir" class="notificacao-card">
        <img src="/static/images/lixeira_branca.svg" style="width:22px;height:22px;filter:invert(1);margin-right:8px;">
        Usuário excluído com sucesso!
    </div>
    <script>
    $(function(){
        $('.btn-excluir-usuario').click(function(){
            var id = $(this).data('id');
            $.ajax({
                url: '/admin/excluir_usuario/' + id,
                type: 'POST',
                success: function(){
                    $('#notificacao-excluir').fadeIn(200);
                    setTimeout(function(){
                        $('#notificacao-excluir').fadeOut(400);
                        $('.admin-tab.active').click();
                    }, 1800);
                },
                error: function(){
                    $('#notificacao-excluir').text('Erro ao excluir usuário.').fadeIn(200);
                    setTimeout(function(){
                        $('#notificacao-excluir').fadeOut(400);
                    }, 2000);
                }
            });
        });
    });
    </script>'''
    return html
    if not nome:
        return '', 403
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    if not usuario or usuario['email'] != 'edersonluan@exemplo.com':
        conn.close()
        return '', 403
    # Excluir dependências primeiro
    cursor.execute('DELETE FROM progresso_usuario WHERE usuario_id = ?', (user_id,))
    cursor.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return ''

@app.route('/admin/excluir_usuario/<int:user_id>', methods=['POST'])
def excluir_usuario(user_id):
    nome = session.get('usuario')
    if not nome:
        return '', 403
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    if not usuario or usuario['email'] != 'edersonluan@exemplo.com':
        conn.close()
        return '', 403
    # Excluir dependências primeiro
    cursor.execute('DELETE FROM progresso_usuario WHERE usuario_id = ?', (user_id,))
    cursor.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return ''

@app.route('/admin/painel/cursos')
def admin_painel_cursos():
    nome = session.get('usuario')
    if not nome:
        return '', 403
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    if not usuario or usuario['email'] != 'edersonluan@exemplo.com':
        conn.close()
        return '', 403
    cursor.execute('SELECT id, titulo, descricao, criador_id FROM cursos ORDER BY id')
    cursos = cursor.fetchall()
    conn.close()
    html = '<h2>Cursos cadastrados</h2>'
    html += '<table style="width:100%;border-collapse:collapse;margin-top:18px;">'
    html += '<tr style="background:#f0b41b;color:#1a2a3f;font-weight:800;"><th style="padding:8px;">ID</th><th style="padding:8px;">Título</th><th style="padding:8px;">Descrição</th><th style="padding:8px;">Criador (ID)</th></tr>'
    for c in cursos:
        html += f'<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">{c[0]}</td><td style="padding:8px;">{c[1]}</td><td style="padding:8px;">{c[2]}</td><td style="padding:8px;">{c[3] if c[3] else "-"}</td></tr>'
    html += '</table>'
    return html
def registrar_curso(titulo, descricao, criador_id, instrutor=None, duracao=None, nivel=None, categoria=None, publicado=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cursos (titulo, descricao, criador_id, instrutor, duracao, nivel, categoria, publicado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (titulo, descricao, criador_id, instrutor, duracao, nivel, categoria, publicado))
    conn.commit()
    conn.close()

@app.route('/admin/adicionar_tag/<int:user_id>', methods=['POST'])
def adicionar_tag_usuario(user_id):
    nome = session.get('usuario')
    if not nome:
        return '', 403
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,))
    usuario = cursor.fetchone()
    if not usuario or usuario['email'] != 'edersonluan@exemplo.com':
        conn.close()
        return '', 403
    nova_tag = request.form.get('tag', '').strip()
    cursor.execute('UPDATE usuarios SET tag = ? WHERE id = ?', (nova_tag, user_id))
    conn.commit()
    conn.close()
    return 'Tag atualizada com sucesso!'



if __name__ == '__main__':
    app.run(debug=True)
