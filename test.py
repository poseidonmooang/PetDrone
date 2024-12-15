import cv2
import mediapipe as mp
import numpy as np
from tensorflow.keras.models import load_model

# 제스처 명과 동작 설정
actions = ['come', 'away', 'spin', 'sit', 'up', 'bang']
seq_length = 30

# 딥러닝 모델 로드
model = load_model('models/model.keras')

# MediaPipe Hands 모델 설정
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def gesture_control():
    # 노트북 카메라 캡처
    cap = cv2.VideoCapture(0)

    seq = []
    counter = 0  # 연속 제스처 카운트
    last_action = 'None'  # 마지막 인식된 제스처
    gesture_in_progress = False  # 행동 수행 중 여부 플래그

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("카메라에서 프레임을 가져올 수 없습니다.")
            break

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(img)

        if result.multi_hand_landmarks is not None:
            for res in result.multi_hand_landmarks:
                joint = np.zeros((21, 4))
                for j, lm in enumerate(res.landmark):
                    joint[j] = [lm.x, lm.y, lm.z, lm.visibility]

                # 관절 간의 각도 계산
                v1 = joint[[0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 0, 13, 14, 15, 0, 17, 18, 19], :3]
                v2 = joint[[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], :3]
                v = v2 - v1
                v = v / np.linalg.norm(v, axis=1)[:, np.newaxis]

                angle = np.arccos(np.einsum('nt,nt->n',
                                            v[[0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18], :],
                                            v[[1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19], :]))

                angle = np.degrees(angle)

                d = np.concatenate([joint.flatten(), angle])
                seq.append(d)

                mp_drawing.draw_landmarks(frame, res, mp_hands.HAND_CONNECTIONS)

                if len(seq) < seq_length:
                    continue

                input_data = np.expand_dims(np.array(seq[-seq_length:], dtype=np.float32), axis=0)

                # 제스처 예측
                y_pred = model.predict(input_data).squeeze()
                i_pred = int(np.argmax(y_pred))
                conf = y_pred[i_pred]

                if counter == 0:
                    if conf >= 0.9:  # 확신도가 0.9 이상일 때만 새로운 제스처 시작
                        action = actions[i_pred]
                        last_action = action
                        counter = 1
                        print(f"새로운 제스처 {action} 시작! 카운터 초기화: {counter}")
                    else:
                        print(f"확신도 낮음. 제스처 무시 ({actions[i_pred]}, 신뢰도: {conf:.2f})")
                elif counter < 5 or counter > 0:
                    if action == actions[i_pred]:  # 동일한 제스처일 경우
                        counter += 1
                        print(f"같은 제스처 {action} 확인. 카운터 증가: {counter}")
                    elif conf >= 0.9:  # 다른 제스처가 0.9 이상의 확신도로 인식될 경우
                        action = actions[i_pred]
                        last_action = action
                        counter = 0
                        print(f"새로운 제스처 {action} 전환! 카운터 초기화: {counter}")
                    else:
                        print(f"제스처 변경 없음. 현재 제스처: {action}, 인식된 제스처: {actions[i_pred]}, 신뢰도: {conf:.2f}")

                elif counter >= 5:  # 행동 실행 조건
                    if gesture_in_progress:
                        print("제스처 실행 중, 다른 제스처는 실행되지 않습니다.")
                        continue

                    print(f"제스처 {action} 연속 5회 확인! 행동 출력.")

                    gesture_in_progress = True
                    print(f"동작: {action}")  # 동작을 프린트로 출력

                    # 행동 완료 후 초기화
                    counter = 0
                    action = 'None'
                    seq = []
                    gesture_in_progress = False
        else:
            print("손이 감지되지 않았습니다.")

        # 영상 출력
        cv2.imshow('Camera Feed', frame)

        if cv2.waitKey(1) == ord('q'):
            print("프로그램 종료")
            break

    cap.release()
    cv2.destroyAllWindows()

# 제스처 인식 실행
gesture_control()