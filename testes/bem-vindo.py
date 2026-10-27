from pathlib import Path

from PIL import Image, ImageDraw

imagem = Image.new("RGB", (800, 400), "black")

desenho = ImageDraw.Draw(imagem)

desenho.text((50, 50), "Bem-vindo!", fill="white")

imagem.save(Path(__file__).resolve().parent / "teste.png")

