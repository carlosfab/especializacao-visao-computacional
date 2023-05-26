# Importando os pacotes necessários
from scipy.spatial import distance as dist
from imutils.video import VideoStream
from imutils import face_utils
from threading import Thread
import numpy as np
import playsound
import argparse
import imutils
import time
import dlib
import cv2
import matplotlib.pyplot as plt


# Função para tocar um alarme
def tocar_alarme(caminho):
    # Toca um som de alarme
    playsound.playsound(caminho)

# Função para calcular a relação de aspecto dos olhos (EAR)
def calcular_ear(olho):
    # Calcula as distâncias euclidianas entre os dois conjuntos de
    # marcos oculares verticais (coordenadas x, y)
    A = dist.euclidean(olho[1], olho[5])
    B = dist.euclidean(olho[2], olho[4])

    # Calcula a distância euclidiana entre os marcos oculares horizontais
    # (coordenadas x, y)
    C = dist.euclidean(olho[0], olho[3])

    # Calcula o EAR
    ear = (A + B) / (2.0 * C)

    # Retorna o EAR
    return ear

# Constroi o parser dos argumentos
ap = argparse.ArgumentParser()
ap.add_argument("-a", "--alarme", type=int, default="0",
                help="Usar alarme sonoro?")
ap.add_argument("-w", "--webcam", type=int, default=0,
                help="índice da webcam no sistema")
args = vars(ap.parse_args())

# Define duas constantes, uma para o EAR que indica
# um piscar de olhos e uma segunda constante para o número de quadros consecutivos
# que o olho deve estar abaixo do limiar para disparar o alarme
LIMIAR_EAR = 0.25
QTD_CONSEC_FRAMES = 20

# Inicializa o contador de quadros e uma variável booleana para
# indicar se o alarme está tocando
CONTADOR = 0
ALARME_ON = False

# Inicializa o detector de rosto do dlib (baseado em HOG) e cria
# o preditor de marcos faciais
print("[INFO] Carregando preditor de marcos faciais...")
detector = dlib.get_frontal_face_detector()
preditor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# Pega os índices dos marcos faciais para o olho esquerdo e
# direito, respectivamente
(inicio_esq, fim_esq) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(inicio_dir, fim_dir) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

# Inicia a thread de fluxo de vídeo
print("[INFO] Iniciando thread de fluxo de vídeo...")
vs = VideoStream(src=args["webcam"]).start()
time.sleep(1.0)

# Desenha a figura para que as animações funcionem
y = [None] * 100
x = np.arange(0,100)
fig = plt.figure()
ax = fig.add_subplot(111)
li, = ax.plot(x, y)

# Faz loop nos quadros do fluxo de vídeo
while True:
    # Pega o quadro do fluxo de vídeo em arquivo, redimensiona
    # e converte para escala de cinza
    frame = vs.read()
    frame = imutils.resize(frame, width=700)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detecta rostos no quadro em escala de cinza
    rects = detector(gray, 0)

    # Faz loop nas detecções de rosto
    for rect in rects:
        # Determina os marcos faciais para a região do rosto, depois
        # converte os marcos faciais (coordenadas x, y) para um array NumPy
        shape = preditor(gray, rect)
        shape = face_utils.shape_to_np(shape)

        # Extrai as coordenadas do olho esquerdo e direito, depois usa as
        # coordenadas para calcular o EAR para ambos os olhos
        olho_esq = shape[inicio_esq:fim_esq]
        olho_dir = shape[inicio_dir:fim_dir]
        ear_esq = calcular_ear(olho_esq)
        ear_dir = calcular_ear(olho_dir)

        # Calcula a média do EAR para ambos os olhos
        ear = (ear_esq + ear_dir) / 2.0

        # Calcula o casco convexo para o olho esquerdo e direito, depois
        # visualiza cada um dos olhos
        casco_olho_esq = cv2.convexHull(olho_esq)
        casco_olho_dir = cv2.convexHull(olho_dir)
        cv2.drawContours(frame, [casco_olho_esq], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [casco_olho_dir], -1, (0, 255, 0), 1)

        # remove o primeiro elemento e adiciona o ear calculado
        y.pop(0)
        y.append(ear)

        # Atualiza o canvas imediatamente
        plt.xlim([0, 100])
        plt.ylim([0, 0.4])
        ax.relim()
        ax.autoscale_view(True, True, True)
        fig.canvas.draw()
        plt.show(block=False)
        # define os novos dados
        li.set_ydata(y)

        fig.canvas.draw()

        time.sleep(0.01)

        # Verifica se o EAR está abaixo do limiar de piscar de olhos,
        # e se estiver, incrementa o contador de quadros de piscar
        if ear < LIMIAR_EAR:
            CONTADOR += 1

            # se os olhos estavam fechados por um número suficiente de
            # quadros, então soa o alarme
            if CONTADOR >= QTD_CONSEC_FRAMES:
                # se o alarme não está ligado, ligue-o
                if not ALARME_ON:
                    ALARME_ON = True

                    # verifica se um arquivo de alarme foi fornecido,
                    # e se sim, inicia uma thread para ter o som do alarme
                    # tocado em segundo plano
                    if args["alarme"] != 0:
                        t = Thread(target=tocar_alarme,
                                   args=("alarm.wav",))
                        t.deamon = True
                        t.start()

                # desenha um alarme no quadro
                cv2.putText(frame, "[ALERTA] SONOLENCIA!", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # caso contrário, o EAR não está abaixo do limiar de piscar,
        # então reseta o contador e o alarme
        else:
            CONTADOR = 0
            ALARME_ON = False

            # desenha o EAR calculado no quadro para ajudar
            # com a depuração e ajuste dos limiares de EAR corretos
            # e contadores de quadros
        cv2.putText(frame, "EAR: {:.2f}".format(ear), (300, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # mostra o quadro
    cv2.imshow("Frame", frame)
    tecla = cv2.waitKey(1) & 0xFF

    # se a tecla `q` foi pressionada, quebra o loop
    if tecla == ord("q"):
        break

# faz uma limpeza geral
cv2.destroyAllWindows()
vs.stop()
