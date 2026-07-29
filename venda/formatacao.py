
def formataco(dados: any, filial: str, depto: str):
    
    dadosFilial = (
        dados
        if filial == 'todos'
        else [item for item in dados if item['CODFILIAL'] == filial]
    )
    
    dadosDepto = (
        dadosFilial
        if depto.lower == 'todos'
        else [
            item for item in dadosFilial 
            if item['DEPARTAMENTO'].upper() == depto.upper()]
    )
    
    resposta = {}
   
    for item in dadosDepto:
        codfilial = item["CODFILIAL"] 
        
        if codfilial not in resposta:
            resposta[codfilial] = {
                "CODFILIAL": codfilial,
                "VENDA": 0,
                "CUSTO": 0,
            }
            
        resposta[codfilial]["VENDA"] += float(item["VENDA"] or 0)
        resposta[codfilial]["CUSTO"] += float(item["CUSTO"] or 0)
        
    resposta = list(resposta.values())
   
    print(resposta)
        
