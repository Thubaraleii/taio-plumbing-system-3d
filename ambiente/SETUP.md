# Ambiente Python para GemPy

O GemPy roda em Python (fora do Blender). O Blender entra só na etapa final, importando os arquivos .obj exportados pelo GemPy — não precisa (e não dá certo) rodar o GemPy dentro do interpretador Python do Blender.

## Opção recomendada: ambiente virtual dedicado

No Windows, com Python 3.10+ instalado:

```
cd 1_Modelo_3D_Taio
python -m venv venv
venv\Scripts\activate
pip install -r ambiente\requirements.txt
```

## Opção Conda (se preferir)

```
conda create -n taio_gempy python=3.10
conda activate taio_gempy
pip install -r ambiente\requirements.txt
```

## Verificando a instalação

Depois de instalar, rode:

```
python scripts\00_verificar_ambiente.py
```

Se aparecer "Ambiente OK" no final, está tudo pronto para seguir para os próximos scripts.

## Nota sobre versões do GemPy

O GemPy passou por uma reformulação grande de API (a versão usada e testada aqui é a "v3", pacote `gempy==2026.0.3`, que usa `gp.create_geomodel`, `gp.map_stack_to_surfaces`, `gp.compute_model`, etc.). Tutoriais antigos na internet (de 2021-2022) usam uma API bem diferente (`gp.create_model`, `gp.init_data`...) — se for buscar exemplos, prefira a documentação/exemplos atuais do GemPy (gempy.org) para não se confundir com a sintaxe antiga.
