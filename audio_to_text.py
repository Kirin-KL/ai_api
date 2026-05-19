# Улучшенная модель с Dropout и BatchNormalization
# def create_improved_model(input_shape, num_classes):
#     inputs = keras.Input(shape=input_shape)
#
#     # Первый блок
#     x = keras.layers.Conv2D(32, (3,3), activation="relu", padding="same")(inputs)
#     x = keras.layers.BatchNormalization()(x)
#     x = keras.layers.MaxPooling2D((2,2))(x)
#     x = keras.layers.Dropout(0.1)(x)
#
#     # Второй блок
#     x = keras.layers.Conv2D(64, (3,3), activation="relu", padding="same")(x)
#     x = keras.layers.BatchNormalization()(x)
#     x = keras.layers.MaxPooling2D((2,2))(x)
#     x = keras.layers.Dropout(0.1)(x)
#
#     # Третий блок
#     x = keras.layers.Conv2D(128, (3,3), activation="relu", padding="same")(x)
#     x = keras.layers.BatchNormalization()(x)
#     x = keras.layers.MaxPooling2D((2,2))(x)
#     x = keras.layers.Dropout(0.1)(x)
#
#     # Четвертый блок
#     x = keras.layers.Conv2D(256, (3,3), activation="relu", padding="same")(x)
#     x = keras.layers.BatchNormalization()(x)
#     x = keras.layers.GlobalAveragePooling2D()(x)
#     x = keras.layers.Dropout(0.3)(x)
#
#     # Dense слои
#     x = keras.layers.Dense(256, activation="relu")(x)
#     x = keras.layers.BatchNormalization()(x)
#     x = keras.layers.Dropout(0.5)(x)
#
#     x = keras.layers.Dense(128, activation="relu")(x)
#     x = keras.layers.Dropout(0.3)(x)
#
#     outputs = keras.layers.Dense(num_classes, activation="softmax")(x)
#
#     return keras.Model(inputs, outputs)

import keras
import tensorflow as tf
import os
import time
from pydub import AudioSegment
import librosa
import numpy as np
from pathlib import Path



# Временный вариант +++++++++++++

from pathlib import Path
from difflib import get_close_matches
from faster_whisper import WhisperModel


COMMANDS = [
    "Да",
    "Нет",
    "Вода",
    "Электричество",
    "Оператор",
    "Задолжность",
]



COMMAND_ALIASES = {
    "Да": [
        "да",
        "ага",
    ],
    "Нет": [
        "нет",
        "не",
    ],
    "Вода": [
        "вода",
        "воды",
        "воду",
    ],
    "Электричество": [
        "электричество",
        "электричества",
        "свет",
        "электроэнергия",
    ],
    "Оператор": [
        "оператор",
        "оператора",
        "соедините с оператором",
    ],
    "Задолжность": [
        "задолжность",
        "задолженность",
        "долг",
        "задолженности",
    ],
}


model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


def audio_to_command(wav_path: str) -> str | None:
    path = Path(wav_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {wav_path}")

    if path.suffix.lower() != ".wav":
        raise ValueError("Функция принимает только WAV-файлы")

    segments, info = model.transcribe(
        str(path),
        language="ru",
        beam_size=5,
        vad_filter=True
    )

    recognized_text = " ".join(segment.text for segment in segments)
    normalized_text = normalize_text(recognized_text)

    if not normalized_text:
        return None

    # 1. Точное совпадение всей фразы
    for command, aliases in COMMAND_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_text(alias)

            if normalized_text == normalized_alias:
                return command

    # 2. Совпадение по словам, а не по подстроке
    words = normalized_text.split()

    for command, aliases in COMMAND_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_text(alias)

            if " " not in normalized_alias and normalized_alias in words:
                return command

    # 3. Нечёткое сравнение
    all_aliases = []
    alias_to_command = {}

    for command, aliases in COMMAND_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_text(alias)
            all_aliases.append(normalized_alias)
            alias_to_command[normalized_alias] = command

    best_matches = get_close_matches(
        normalized_text,
        all_aliases,
        n=1,
        cutoff=0.85
    )

    if best_matches:
        return alias_to_command[best_matches[0]]

    return None


def normalize_text(text: str) -> str:
    return (
        text.lower()
        .replace("ё", "е")
        .replace(".", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
        .replace(":", "")
        .replace(";", "")
        .strip()
    )
# Временный вариант +++++++++++++++++++++++

# Общие аудио-константы
SAMPLE_RATE = 16000
N_MELS = 64
N_FFT = 1024

# Константы для цифр
HOP_LENGTH_DIGITS = 256
SAMPLES_DIGITS = 16000  # 1 секунда
DIGIT_CLASSES = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]

# Константы для команд
HOP_LENGTH_COMMANDS = 512
DURATION_COMMANDS = 2.0
SAMPLES_COMMANDS = int(SAMPLE_RATE * DURATION_COMMANDS)
COMMAND_CLASSES = ["Да", "Нет", "Электричество", "Вода", "Оператор", "Задолжность"]

# Загрузка моделей
model_path_digits = "neural_network/digits/fix_digits_v1.keras"
print("Загружаю модель для цифр из:", os.path.abspath(model_path_digits))
model_digit = tf.keras.models.load_model(model_path_digits)
print("Модель распознавания цифр загружена")

model_path_command = "neural_network/comand/fix_comand_v1.keras"
print("Загружаю модель для команд из:", os.path.abspath(model_path_command))
model_command = tf.keras.models.load_model(model_path_command)
print("Модель распознавания команд загружена")

# Загрузка модели Silero VAD
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
model_silero_VAD = load_silero_vad()

# Функция для выравнивания длинны отрезков аудио
def fix_length(samples, target_len):
    if len(samples) > target_len:
        return samples[:target_len]
    else:
        return np.pad(samples, (0, target_len - len(samples)))

# Перевод аудио в массив numpy
def audiosegment_to_np(segment: AudioSegment):
    samples = np.array(segment.get_array_of_samples()).astype(np.float32)

    if segment.channels > 1:
        samples = samples.reshape((-1, segment.channels))
        samples = samples.mean(axis=1)

    samples /= np.iinfo(segment.array_type).max
    return samples

# Нахождение отрезков с речью с помощью sileroVAD
def find_speech_fragments(file_wav):
    wav = read_audio(file_wav)
    speech_timestamps = get_speech_timestamps(
        wav,
        model_silero_VAD,
        return_seconds=True,
        min_speech_duration_ms=150,
        min_silence_duration_ms=100,
        speech_pad_ms=120
    )
    return speech_timestamps

# Перевод аудио в mel спектрограммы
def audio_to_melspec_generic(
    y,
    sample_rate=SAMPLE_RATE,
    n_mels=N_MELS,
    n_fft=N_FFT,
    hop_length=HOP_LENGTH_DIGITS
):
    S = librosa.feature.melspectrogram(
        y=y,
        sr=sample_rate,
        n_mels=n_mels,
        n_fft=n_fft,
        hop_length=hop_length
    )
    S_db = librosa.power_to_db(S, ref=np.max)
    S_db = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-8)
    return S_db.astype("float32")

# Подготовка аудио ко входу в нейросеть
def prepare_input_for_model(spec):
    spec = np.expand_dims(spec, -1)  # (H, W, 1)
    spec = np.expand_dims(spec, 0)   # (1, H, W, 1)
    return spec

# Распознавание цифр
def audio_to_digits(file_wav, model=model_digit):

    file_wav = str(file_wav)

    audio = AudioSegment.from_wav(file_wav)
    audio = audio.set_frame_rate(SAMPLE_RATE)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)

    print("Аудио загружено")

    timestamps = find_speech_fragments(file_wav)
    print("Получены временные метки")

    digits_arr = []

    for t in timestamps:
        start_ms = int(t['start'] * 1000)
        end_ms = int(t['end'] * 1000)
        segment = audio[start_ms:end_ms]

        samples = audiosegment_to_np(segment)
        samples = fix_length(samples, SAMPLES_DIGITS)

        spec = audio_to_melspec_generic(
            samples,
            sample_rate=SAMPLE_RATE,
            n_mels=N_MELS,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH_DIGITS
        )
        model_input = prepare_input_for_model(spec)

        probs = model.predict(model_input, verbose=0)[0]
        pred_idx = np.argmax(probs)
        pred_digit = DIGIT_CLASSES[pred_idx]

        digits_arr.append(pred_digit)

    num_digits = len(digits_arr)
    return digits_arr, num_digits

def safe_load_audio_for_commands(path):
    try:
        y, _ = librosa.load(path, sr=SAMPLE_RATE)
    except Exception as e:
        print(f"Ошибка при чтении {path}: {e}")
        return None

    y = fix_length(y, SAMPLES_COMMANDS)
    return y

# Распознавание команд
# def audio_to_command(file_wav, model=model_command):
#     """
#     Распознаёт команду в аудио любой длины.
#     Использует VAD → классифицирует каждый фрагмент → выбирает лучший.
#     """
#
#     file_wav = str(file_wav)
#
#     # --- 1. Загружаем аудио ---
#     audio = AudioSegment.from_wav(file_wav)
#     audio = audio.set_frame_rate(SAMPLE_RATE)
#     audio = audio.set_channels(1)
#     audio = audio.set_sample_width(2)
#
#     # --- 2. Ищем фрагменты речи ---
#     timestamps = find_speech_fragments(file_wav)
#     print(timestamps)
#
#     if len(timestamps) == 0:
#         return None, None  # нет речи
#
#     best_prob = -1
#     best_command = None
#     best_full_probs = None
#
#     # --- 3. Обрабатываем каждый фрагмент ---
#     for t in timestamps:
#         start_ms = int(t["start"] * 1000)
#         end_ms   = int(t["end"] * 1000)
#
#         segment = audio[start_ms:end_ms]
#
#         samples = audiosegment_to_np(segment)
#
#         # Приводим к 2 секундам (как в обучении)
#         samples = fix_length(samples, SAMPLES_COMMANDS)
#
#         # Мел-спектр с hop_length=512
#         spec = audio_to_melspec_generic(
#             samples,
#             sample_rate=SAMPLE_RATE,
#             n_mels=N_MELS,
#             n_fft=N_FFT,
#             hop_length=HOP_LENGTH_COMMANDS
#         )
#
#         model_input = prepare_input_for_model(spec)
#
#         probs = model.predict(model_input, verbose=0)[0]
#         pred_idx = np.argmax(probs)
#         pred_prob = probs[pred_idx]
#         pred_command = COMMAND_CLASSES[pred_idx]
#
#         # --- 4. Выбираем фрагмент с максимальной уверенностью ---
#         if pred_prob > best_prob:
#             best_prob = pred_prob
#             best_command = pred_command
#             best_full_probs = probs
#
#     return best_command, best_full_probs


# command, prob = audio_to_command_vad_best("neural_network/Исходные записи/Вода_абра.wav")
# print(command, prob)



