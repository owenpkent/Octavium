from PIL import Image

img = Image.open("Octavium icon.png")
img.save("Octavium.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("Converted Octavium icon.png to Octavium.ico")
