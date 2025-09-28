### Título do PR

<use um formato claro e conciso, como "tipo: descrição">
<Exemplo: feat: Adiciona novo componente de botão>
<Exemplo: fix: Corrige bug no formulário de login>
<Exemplo: docs: Atualiza a documentação sobre a API de usuários>

---

### Descrição
- **O que este PR faz?** Descreva o problema que você está resolvendo ou a nova funcionalidade que está implementando.
- **Por que esta mudança é necessária?** Explique o contexto e a razão para a alteração.

---

### Tarefa Relacionada
<Vincule este PR a uma issue ou ticket existente no GitHub, se houver.>
- **Closes #123** <--- (Isso fecha a issue automaticamente quando o PR é mesclado)

---

### Tipo de Mudança
- [ ] Nova feature
- [ ] Bug fix
- [ ] Melhoria de performance/refatoração
- [ ] Documentação
- [ ] Outro (descreva abaixo)

---

### Mudanças Propostas
<Detalhe as mudanças técnicas de forma clara e objetiva. Use uma lista com bullets.>
- Adicionado o arquivo `novo_componente.js`.
- Atualizado o `Login.js` para usar o novo componente.
- Removida a lógica antiga para validação de formulário.

---

### Como Testar
<Forneça instruções passo a passo para o revisor testar suas mudanças localmente.>
1.  Clone esta branch: `git checkout sua-branch`
2.  Rode `npm install` para instalar as novas dependências.
3.  Inicie o servidor de desenvolvimento: `npm start`
4.  Navegue até `http://localhost:3000/login`
5.  Verifique se o novo componente está sendo renderizado corretamente e se a nova funcionalidade funciona como esperado.

---

### Screenshots / Gifs
<Adicione capturas de tela ou GIFs para demonstrar as mudanças visuais. Isso é especialmente útil para alterações na interface do usuário.>
![gif-do-pr](link_para_o_seu_gif_ou_imagem.gif)

---

### Checklist de PR
<Antes de submeter, complete esta checklist.>
- [ ] O meu código segue o guia de estilo do projeto.
- [ ] Eu testei meu código localmente e ele funciona como esperado.
- [ ] Eu atualizei a documentação, se necessário.
- [ ] Eu adicionei testes (se aplicável) que cobrem as minhas mudanças.
- [ ] O meu PR não introduziu novos erros de lint.