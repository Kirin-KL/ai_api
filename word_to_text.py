from importlib import import_module

import torch
torch.set_num_threads(1)
import soundfile as sf
from pathlib import Path


print("Загрузка модели для озвучивания")
model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v5_ru"
    )
print("Модель для озвучивания загружена!")



def speak(text, output_path="output_silero/tts.wav", speaker="kseniya", overwrite=False):
    audio = model.apply_tts(
        text=text,
        speaker=speaker,
        sample_rate=8000
    )

    output_path = Path(output_path)

    # Проверка на существование файла
    if output_path.exists() and not overwrite:
        print(f"Файл {output_path} уже существует. Используйте overwrite=True для перезаписи.")
        return None

    # Создание папки, если её нет
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sf.write(str(output_path), audio.numpy(), 8000)

    print(f"Файл {output_path} создан!")

    return output_path.name


# speak("Ваш лицевой счёт: один, один, один, два, два, два, три, четыре, пять, шесть. Всё верно?")

