# Checkout API — Desafio de correção de bugs

Você entrou no time de uma loja online. A API de checkout (Flask + Python) já está em produção,
mas o suporte abriu alguns chamados. Sua tarefa é **encontrar e corrigir os bugs** sem quebrar
o comportamento que já funciona.

Há **3 bugs** no código de `app/` (fácil, médio e difícil). Não altere os testes.

## Chamados do suporte

1. **#1042**: "Alguns clientes dizem que pagaram frete num pedido que deveria ter saído com frete grátis."
2. **#1057**: "O financeiro achou diferenças de centavos entre o valor dos pedidos e o que foi cobrado no cartão."
3. **#1071**: "O time de estoque diz que os números do sistema não batem com a contagem física
   depois que começamos a fazer estornos."

## Regras de negócio

### Produtos e carrinho
- Valores monetários usam `Decimal`, com 2 casas, e são serializados no JSON como string (`"59.90"`).
- Adicionar ao carrinho um produto que já está nele soma a quantidade, sem criar uma linha nova.
- `quantity` deve ser um inteiro `>= 1`.

### Preço do pedido
- `subtotal` = soma de `preço unitário × quantidade`.
- Cupons (o código não diferencia maiúsculas de minúsculas):

  | Cupom         | Efeito                      | Condição               |
  |---------------|-----------------------------|------------------------|
  | `DESCONTO10`  | 10% de desconto no subtotal | —                      |
  | `MENOS50`     | R$ 50,00 de desconto        | subtotal ≥ R$ 250,00   |
  | `FRETEGRATIS` | frete grátis                | —                      |

- O frete é **R$ 25,00**. Ele é **grátis quando o subtotal já com desconto é de R$ 200,00 ou mais**,
  ou quando o cupom é `FRETEGRATIS`.
- `total = subtotal - desconto + frete`.

### Pagamento
- O cartão precisa ter 16 dígitos. Cartões terminados em `0002` são recusados pela operadora (HTTP 402).
- Parcelamento de **1 a 12 vezes**, sem juros.
- A **soma das parcelas deve ser exatamente igual ao total do pedido**. Todas as parcelas têm o mesmo
  valor (o total dividido pelo número de parcelas, **arredondado para baixo** no centavo), e os centavos que
  sobram vão para a **primeira parcela**. Exemplo: R$ 100,00 em 3x = `33.34, 33.33, 33.33`.
- O checkout é atômico. Se faltar estoque ou o pagamento falhar, nada é cobrado, o estoque fica como
  estava e o carrinho continua com os itens.
- Depois de um checkout com sucesso, o carrinho fica vazio e pode ser usado de novo. **O pedido criado
  precisa manter para sempre os itens que foram comprados.**

### Estorno
- `POST /payments/<id>/refund` recebe `{"amount": "25.00"}`. Sem `amount`, o estorno é do saldo restante.
- Pode haver vários estornos parciais, mas a soma deles nunca pode passar do valor pago (HTTP 409).
- Quando a soma dos estornos chega ao valor pago, o status vira `REFUNDED` e **os itens do pedido voltam
  para o estoque**. Um estorno parcial (`PARTIALLY_REFUNDED`) não devolve nada ao estoque.

## Endpoints

| Método | Rota                         | Descrição                                          |
|--------|------------------------------|----------------------------------------------------|
| GET    | `/products`                  | lista os produtos                                  |
| GET    | `/products/<id>`             | detalhe e estoque de um produto                    |
| POST   | `/carts`                     | cria um carrinho (201)                             |
| GET    | `/carts/<id>`                | mostra o carrinho                                  |
| POST   | `/carts/<id>/items`          | `{"product_id": 1, "quantity": 2}`                 |
| POST   | `/carts/<id>/checkout`       | `{"card_number": "...", "installments": 3, "coupon": "MENOS50"}` (201) |
| GET    | `/orders/<id>`               | detalhe do pedido                                  |
| GET    | `/payments/<id>`             | detalhe do pagamento                               |
| POST   | `/payments/<id>/refund`      | estorno total ou parcial                           |

## Como executar o projeto

### 1. Preparar o ambiente (uma vez só)

Pré-requisito: Python 3.11 ou mais novo.

```powershell
cd C:\Users\rsssh\repos\hackerrank-checkout-bugfix
python -m venv .venv                  # (já criado; só precisa se apagar a pasta .venv)
.venv\Scripts\Activate.ps1            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

> Se o PowerShell bloquear o `Activate.ps1`, rode antes
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, ou use `.venv\Scripts\python -m pytest`
> sem ativar o ambiente.

### 2. Rodar os testes

```powershell
pytest                                         # todos os testes visíveis (pasta tests/)
pytest -v                                      # mostra o nome de cada teste
pytest tests/test_pricing.py                   # só um arquivo
pytest tests/test_pricing.py::test_percent_coupon   # só um teste
pytest -k shipping                             # testes cujo nome contém "shipping"
pytest -x                                      # para no primeiro teste que falhar
pytest --tb=short                              # traceback mais curto
```

Na versão com bugs, **2 testes visíveis falham**. Isso é esperado.

### 3. Subir a API e testar na mão

```powershell
flask --app app run --debug           # http://127.0.0.1:5000 (recarrega quando você salva um arquivo)
```

Em outro terminal (os dados ficam em memória e voltam ao estado inicial quando a API reinicia):

```powershell
curl.exe http://127.0.0.1:5000/products
curl.exe -X POST http://127.0.0.1:5000/carts
curl.exe -X POST http://127.0.0.1:5000/carts/1/items -H "Content-Type: application/json" -d '{\"product_id\": 1, \"quantity\": 2}'
curl.exe -X POST http://127.0.0.1:5000/carts/1/checkout -H "Content-Type: application/json" -d '{\"card_number\": \"4111111111111111\", \"installments\": 3}'
curl.exe http://127.0.0.1:5000/orders/1
curl.exe http://127.0.0.1:5000/payments/1
curl.exe -X POST http://127.0.0.1:5000/payments/1/refund
curl.exe http://127.0.0.1:5000/products/1
```

Ou, no PowerShell puro:

```powershell
$base = "http://127.0.0.1:5000"
$cart = Invoke-RestMethod -Method Post "$base/carts"
Invoke-RestMethod -Method Post "$base/carts/$($cart.id)/items" -ContentType "application/json" -Body '{"product_id": 1, "quantity": 2}'
$order = Invoke-RestMethod -Method Post "$base/carts/$($cart.id)/checkout" -ContentType "application/json" -Body '{"card_number": "4111111111111111", "installments": 3}'
$order
Invoke-RestMethod "$base/payments/$($order.payment_id)"
```

Cartões de teste: `4111111111111111` é aprovado; `4000000000000002` é recusado (402).

## Como validar se as correções estão OK

Assim como na plataforma, a solução é avaliada por **testes automatizados**, e a nota é o
percentual de testes que passam.

- `tests/`: testes **visíveis**. É o que você recebe junto com o desafio.
- `hidden_tests/`: testes **ocultos**, que cobrem casos de borda e regras que os testes visíveis
  não pegam. **Não abra essa pasta** (nem deixe sua IA abrir) até achar que terminou.

Siga esta ordem:

```powershell
# 1) Os testes visíveis passam?
pytest

# 2) Os testes "da plataforma" (visíveis + ocultos) passam?
pytest tests hidden_tests

# 3) Você mexeu só no código, e não nos testes? (as duas saídas têm que vir vazias)
git status --short tests hidden_tests conftest.py pytest.ini
git diff --stat -- tests hidden_tests conftest.py pytest.ini

# 4) Revise o que mudou: a correção deve ser pequena e no lugar certo
git diff
```

O treino está concluído quando **`pytest tests hidden_tests` termina com tudo passando** e o passo 3
não mostra nada.

Dicas:
- Passar só nos testes visíveis normalmente **não** basta. Corrija a **regra de negócio** descrita
  acima, não o caso específico de um teste.
- Para cada chamado, escreva primeiro um teste que reproduz o problema, numa pasta sua
  (ex.: `meus_testes/test_chamados.py`, rodando com `pytest meus_testes`). Veja o teste falhar,
  corrija o código e veja o teste passar. As fixtures `client`, `make_cart` e `stock` de `conftest.py`
  também funcionam ali.
- `pytest` sozinho (ou `pytest .`) nunca roda os testes ocultos; eles só rodam quando você pede
  `pytest tests hidden_tests`.
- Para recomeçar do zero: `git stash` (guarda suas mudanças) ou `git checkout -- app` (descarta as mudanças).

## Usando a IA (Claude Code) neste treino

- Abra **esta pasta** como raiz no VS Code (Arquivo > Abrir Pasta... > `hackerrank-checkout-bugfix`) ou rode
  `claude` de dentro dela. As travas abaixo só valem para sessões iniciadas aqui.
- O `CLAUDE.md` faz do Claude Code um par de programação que **escreve código para você** (testes de reprodução,
  prints de investigação e as correções que você decidir) e **dá dicas**, mas **não entrega as respostas** (qual é
  o bug, onde está, qual é a correção) e **não lê** os testes ocultos, o gabarito nem os rastros da criação do
  desafio. Dicas são por nível e por chamado: peça `dica 1 #1042`, depois `dica 2 #1042`, e assim por diante (vão
  até o nível 4; a correção é sempre decisão sua).
- Travas técnicas, além das instruções: `.claude/settings.json` bloqueia a leitura de `hidden_tests/`,
  `.gabarito/` e dos rastros da criação do desafio, e bloqueia a edição dos testes, do `conftest.py`, do
  `pytest.ini` e das próprias travas; o hook `.claude/hooks/trava_treino.py` barra comandos e arquivos que citem
  essas pastas ou façam buscas recursivas pelo terminal; o `.ignore` tira essas pastas das buscas (inclusive do
  Ctrl+Shift+F do VS Code).
- Para conferir se está tudo ativo: no Claude Code, rode `/permissions` (devem aparecer as regras de "deny") e
  `/hooks` (deve aparecer o `PreToolUse`). Depois peça "leia hidden_tests/test_hidden.py": ele deve recusar ou ser
  bloqueado.
- Não edite nem apague `CLAUDE.md` e `.claude/` durante o treino. Quando terminar, se quiser discutir tudo
  livremente com a IA (inclusive os testes ocultos), apague ou renomeie esses dois.
- Limite: as travas não são um sandbox do sistema operacional. Um script que abra arquivos sem citar o caminho
  passaria; por isso o `CLAUDE.md` também proíbe isso.

## Gabarito

Só leia depois de terminar:

```bash
python -c "import base64;print(base64.b64decode(open('.gabarito/GABARITO.b64').read()).decode())"
```
