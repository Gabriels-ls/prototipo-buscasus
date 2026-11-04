"""Funções auxiliares de texto, datas e máscaras de dados pessoais."""
import re
import unicodedata
from datetime import date, datetime

MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
         "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


def normalizar(texto):
    """Remove acentos, espaços extras e deixa em minúsculas (para busca)."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def so_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def mascarar_cpf(cpf):
    """12345678909 -> ***.456.789-**"""
    if not cpf or len(cpf) != 11:
        return "Não informado"
    return f"***.{cpf[3:6]}.{cpf[6:9]}-**"


def mascarar_cns(cns):
    """700123456789012 -> 700 **** **** 9012"""
    if not cns or len(cns) != 15:
        return "Não informado"
    return f"{cns[:3]} **** **** {cns[-4:]}"


def mascarar_telefone(telefone):
    """47991234567 -> (47) 9 ****-4567"""
    digitos = so_digitos(telefone)
    if len(digitos) != 11:
        return "Não informado"
    return f"({digitos[:2]}) {digitos[2]} ****-{digitos[-4:]}"


def para_data(valor):
    if isinstance(valor, (date, datetime)):
        return valor
    return datetime.fromisoformat(valor)


def data_br(valor):
    return para_data(valor).strftime("%d/%m/%Y")


def hora_br(valor):
    return para_data(valor).strftime("%H:%M")


def mes_ano(valor):
    d = para_data(valor)
    return f"{MESES[d.month - 1]} {d.year}"


def idade(nascimento, hoje=None):
    nasc = para_data(nascimento)
    hoje = hoje or date.today()
    anos = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
    return anos


def tempo_relativo(valor, agora=None):
    """Descreve há quanto tempo algo aconteceu: 'há 2 h', 'há 3 dias'."""
    agora = agora or datetime.now()
    segundos = (agora - para_data(valor)).total_seconds()
    if segundos < 60:
        return "agora"
    minutos = int(segundos // 60)
    if minutos < 60:
        return f"há {minutos} min"
    horas = minutos // 60
    if horas < 24:
        return f"há {horas} h"
    dias = horas // 24
    if dias == 1:
        return "ontem"
    return f"há {dias} dias"


def iniciais(nome):
    partes = [p for p in nome.split() if p.lower() not in {"da", "de", "do", "das", "dos", "e"}]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[-1][0]).upper()
