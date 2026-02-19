import requests
import time
import pandas as pd

# --- CONFIGURAÇÕES ---
TOKEN = '' 
NOME_PRODUTO = ''
LIMITE_MINIMO =     
URL_BASE = 'https://api.tiny.com.br/api2'

def buscar_produto_por_nome(nome):
    url = f"{URL_BASE}/produtos.pesquisa.php"
    payload = {'token': TOKEN, 'formato': 'JSON', 'pesquisa': nome}
    try:
        response = requests.post(url, data=payload)
        data = response.json()
        if data['retorno']['status'] == 'OK':
            return data['retorno']['produtos']
    except:
        pass
    return []

def obter_detalhes(id_produto):
    url = f"{URL_BASE}/produto.obter.php"
    payload = {'token': TOKEN, 'formato': 'JSON', 'id': id_produto}
    try:
        response = requests.post(url, data=payload)
        data = response.json()
        if data['retorno']['status'] == 'OK':
            return data['retorno']['produto']
    except:
        pass
    return None

def obter_saldo_multiempresa(id_produto):
    """ 
    Busca o Saldo Disponível oficial do Tiny.
    Isso considera as regras de Multiempresa e Reservas automaticamente.
    """
    url = f"{URL_BASE}/produto.obter.estoque.php"
    payload = {'token': TOKEN, 'formato': 'JSON', 'id': id_produto}
    
    try:
        response = requests.post(url, data=payload)
        data = response.json()
        
        if data['retorno']['status'] == 'OK':
            prod = data['retorno']['produto']
            
            # AQUI ESTÁ A MUDANÇA:
            # Pegamos direto o 'saldo_disponivel' que o ERP calcula.
            # Ele já desconta reservas e soma multiempresa se configurado.
            if 'saldo_disponivel' in prod:
                return float(prod['saldo_disponivel'])
            else:
                # Caso o ERP não retorne o campo (raro), faz o cálculo básico
                return float(prod.get('saldo', 0)) - float(prod.get('saldo_reservado', 0))
            
    except Exception as e:
        print(f"Erro ao consultar estoque: {e}")
        
    return 0

def main():
    print(f"🔎 Buscando '{NOME_PRODUTO}' (Saldo Disponível Multiempresa)...")
    produtos = buscar_produto_por_nome(NOME_PRODUTO)
    
    if not produtos:
        print("❌ Produto não encontrado.")
        return

    lista_repor = []
    lista_geral = []

    for item in produtos:
        prod = item['produto']
        detalhes = obter_detalhes(prod['id'])
        if not detalhes: continue

        if 'variacoes' in detalhes:
            print(f"   Lendo grade de: {prod['nome']}...")
            for var in detalhes['variacoes']:
                v_dados = var.get('variacao', var)
                v_id = v_dados['id']
                
                grade = v_dados.get('grade', {})
                desc_grade = " - ".join([f"{v}" for k,v in grade.items()])
                nome_completo = f"{prod['nome']} ({desc_grade})"
                
                time.sleep(0.3) 
                
                # Busca o saldo inteligente
                saldo = obter_saldo_multiempresa(v_id)
                
                lista_geral.append({
                    'Produto': nome_completo,
                    'ID': v_id,
                    'Saldo Disponível': saldo
                })

                if saldo <= LIMITE_MINIMO:
                    print(f"⚠️  ALERTA: {nome_completo} | Disponível: {saldo}")
                    lista_repor.append({
                        'Produto': nome_completo,
                        'Saldo Disponível': saldo,
                        'Status': 'COMPRAR URGENTE'
                    })
        else:
            saldo = obter_saldo_multiempresa(prod['id'])
            
            lista_geral.append({'Produto': prod['nome'], 'Saldo Disponível': saldo})
            
            if saldo <= LIMITE_MINIMO:
                print(f"⚠️  ALERTA: {prod['nome']} | Disponível: {saldo}")
                lista_repor.append({'Produto': prod['nome'], 'Saldo Disponível': saldo})

    # --- GERAÇÃO DO EXCEL ---
    nome_arquivo = "estoque_multiempresa.xlsx"
    
    if lista_geral:
        print(f"\n💾 Salvando '{nome_arquivo}'...")
        with pd.ExcelWriter(nome_arquivo) as writer:
            if lista_repor:
                pd.DataFrame(lista_repor).to_excel(writer, sheet_name='Comprar Urgente', index=False)
            else:
                pd.DataFrame({'Status': ['Estoque OK']}).to_excel(writer, sheet_name='Comprar Urgente', index=False)

            pd.DataFrame(lista_geral).to_excel(writer, sheet_name='Estoque Geral', index=False)
            
        print("✅ Relatório gerado com sucesso!")
    else:
        print("❌ Nenhum dado para salvar.")

if __name__ == "__main__":
    main()