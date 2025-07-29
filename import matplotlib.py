import matplotlib.pyplot as plt

# Примерные данные
data = [1200, 1250, 1180, 1230, 5000, 1190, 1220, 6000]

# Построение boxplot
plt.figure(figsize=(6, 4))
plt.boxplot(data, vert=False, patch_artist=True)
plt.title('Boxplot по среднему размеру задолженности')
plt.xlabel('Задолженность, рубли')
plt.grid(True)
plt.tight_layout()
plt.show()
