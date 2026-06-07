# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊  charts.py — Генерация графиков для отчёта.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import io
import matplotlib.pyplot as plt
import matplotlib
from aiogram.types import BufferedInputFile
from config import TYPE_LABELS

matplotlib.use("Agg")


def generate_report_charts(stats: dict) -> list:
    labels = [TYPE_LABELS.get(k, k) for k in stats.keys()]
    values = list(stats.values())
    charts = []

    # 📊 Столбчатая диаграмма
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color="#4A90D9")
    ax.set_title("Обращения за сегодня", fontsize=14)
    ax.set_ylabel("Количество")
    ax.set_xlabel("Тип обращения")
    plt.tight_layout()
    charts.append(_fig_to_file(fig, "bar_chart.png"))
    plt.close(fig)

    # 🥧 Круговая диаграмма
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
    ax.set_title("Доля обращений по типам", fontsize=14)
    plt.tight_layout()
    charts.append(_fig_to_file(fig, "pie_chart.png"))
    plt.close(fig)

    # 📉 Горизонтальная диаграмма
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(labels, values, color="#E87040")
    ax.set_title("Рейтинг обращений", fontsize=14)
    ax.set_xlabel("Количество")
    plt.tight_layout()
    charts.append(_fig_to_file(fig, "horizontal_chart.png"))
    plt.close(fig)

    return charts


def _fig_to_file(fig, filename: str) -> BufferedInputFile:
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename=filename)
