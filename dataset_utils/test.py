import json
import pickle
import time
from queue import Queue, Empty
from threading import Thread, Event

import numpy as np
import os
import sys
import cv2

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..' ))
    # import keras_retinanet.bin  # noqa: F401
    # __package__ = "keras_retinanet.bin"
    print(sys.path)


from dataset_utils.tracker import Tracker
from dataset_utils.warper import decode_3dbb, get_transform_matrix, get_transform_matrix_with_criterion
from dataset_utils.geometry import distance, computeCameraCalibration
from dataset_utils.writer import Writer
from keras_retinanet.utils.image import preprocess_image
from keras import backend as K

import keras_retinanet.models


def test_video(model, video_path, json_path, im_w, im_h, batch, name, pair, out_path=None, compare=False, online=True):
    with open(json_path, 'r+') as file:
        # with open(os.path.join(os.path.dirname(json_path), 'system_retinanet_first.json'), 'r+') as file:
        structure = json.load(file)
        camera_calibration = structure['camera_calibration']

    vp1, vp2, vp3, _, _, _ = computeCameraCalibration(camera_calibration["vp1"], camera_calibration["vp2"],
                                                      camera_calibration["pp"])
    vp1 = vp1[:-1] / vp1[-1]
    vp2 = vp2[:-1] / vp2[-1]
    vp3 = vp3[:-1] / vp3[-1]

    cap = cv2.VideoCapture(os.path.join(video_path, 'video.avi'))
    mask = cv2.imread(os.path.join(video_path, 'video_mask.png'), 0)

    ret, frame = cap.read()

    if pair == '12':
        M, IM = get_transform_matrix_with_criterion(vp1, vp2, mask, im_w, im_h)
        vp1_t = np.array([vp3], dtype="float32")
        vp1_t = np.array([vp1_t])

    elif pair == '23':
        M, IM = get_transform_matrix_with_criterion(vp3, vp2, mask, im_w, im_h)

    mg = np.array(np.meshgrid(range(im_w), range(im_h)))
    mg = np.reshape(np.transpose(mg, (1, 2, 0)), (im_w * im_h, 2))
    mg = np.array([[point] for point in mg]).astype(np.float32)
    map = np.reshape(cv2.perspectiveTransform(mg, np.array(IM)), (im_h, im_w, 2))

    if out_path is not None:
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        out = cv2.VideoWriter(out_path, fourcc, 25.0, (frame.shape[1], frame.shape[0]))

    q_frames = Queue(10)
    q_images = Queue(10)
    q_predict = Queue(10)
    e_stop = Event()

    vid_name = os.path.basename(os.path.normpath(video_path))

    def read():
        while (cap.isOpened() and not e_stop.isSet()):
            # read_time = time.time()
            images = []
            frames = []
            for _ in range(batch):
                ret, frame = cap.read()
                if not ret:
                    cap.release()
                    continue
                frames.append(frame)
                image = cv2.bitwise_and(frame, frame, mask=mask)
                # t_image = cv2.warpPerspective(image, M, (im_w, im_h), borderMode=cv2.BORDER_CONSTANT)
                t_image = cv2.remap(image, map, None, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                # cv2.imshow('transform', t_image)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     e_stop.set()
                # t_image = t_image[:, :, ::-1]
                t_image = preprocess_image(t_image)
                images.append(t_image)
            # print("Read FPS: {}".format(batch / (time.time() - read_time)))
            q_images.put(images)
            q_frames.put(frames)

    def read_offline():
        while (cap.isOpened() and not e_stop.isSet()):
            # read_time = time.time()
            images = []
            for _ in range(batch):
                ret, frame = cap.read()
                if not ret:
                    cap.release()
                    continue
                image = cv2.bitwise_and(frame, frame, mask=mask)
                t_image = cv2.remap(image, map, None, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                t_image = preprocess_image(t_image)
                images.append(t_image)
            # print("Read FPS: {}".format(batch / (time.time() - read_time)))
            q_images.put(images)

    def inference():
        # model = keras_retinanet.models.load_model('D:/Skola/PhD/code/keras-retinanet/snapshots/resnet50_converted.h5',
        #                                           backbone_name='resnet50', convert=False)
        while (not e_stop.isSet()):
            try:
                images = q_images.get(timeout=100)
            except Empty:
                break
            gpu_time = time.time()

            # cv2.imshow('t_frame', images[0])
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     e_stop.set()
            y_pred = model.predict_on_batch(np.array(images))
            q_predict.put(y_pred)
            print("GPU FPS: {}".format(batch / (time.time() - gpu_time)))

    def postprocess():
        tracker = Tracker(json_path, M, IM, vp1, vp2, vp3, im_w, im_h, name, pair = pair, threshold=0.2, compare=compare)

        total_time = time.time()
        while not e_stop.isSet():
            try:
                y_pred = q_predict.get(timeout=100)
                frames = q_frames.get(timeout=100)
            except Empty:
                tracker.write()
                break
            # post_time = time.time()
            for i in range(len(frames)):
                boxes = np.concatenate([y_pred[1][i, :, None], y_pred[0][i, :, :], y_pred[3][i, :, :]], 1)
                image_b = tracker.process(boxes, frames[i])
                if out_path is not None:
                    out.write(image_b)
                cv2.imshow('frame', image_b)
                # cv2.imwrite('frame_c0_{}.png'.format(i),image_b)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    e_stop.set()
            # break
            # print("Post FPS: {}".format(batch / (time.time() - post_time)))
            # print("Total FPS: {}".format(batch / (time.time() - total_time)))
            # total_time = time.time()

    def postprocess_offline():
        writer = Writer(json_path, name)
        total_time = time.time()
        frame_cnt = 1
        while not e_stop.isSet():
            try:
                y_pred = q_predict.get(timeout=100)
            except Empty:
                writer.write()
                break
            for i in range(y_pred[0].shape[0]):
                boxes = np.concatenate([y_pred[1][i, :, None], y_pred[0][i, :, :], y_pred[3][i, :, :]], 1)
                writer.process(boxes)
                frame_cnt += 1
            # print("Total FPS: {}".format(batch / (time.time() - total_time)))
            print("Video: {} at frame: {}, FPS: {}".format(vid_name, frame_cnt, frame_cnt / (time.time()-total_time)))
            # total_time = time.time()

    inferencer = Thread(target=inference)

    if online:
        reader = Thread(target=read)
        postprocesser = Thread(target=postprocess)
    else:
        reader = Thread(target=read_offline)
        postprocesser = Thread(target=postprocess_offline)

    reader.start()
    inferencer.start()
    postprocesser.start()

    reader.join()
    inferencer.join()
    postprocesser.join()

    if out_path is not None:
        out.release()
    cv2.destroyAllWindows()


def track_detections(json_path, video_path, im_w, im_h, name, threshold, fake = False):
    print('Tracking: {} for t = {}'.format(name,threshold))

    with open(json_path, 'r+') as file:
        structure = json.load(file)
        camera_calibration = structure['camera_calibration']

    vp1, vp2, vp3, _, _, _ = computeCameraCalibration(camera_calibration["vp1"], camera_calibration["vp2"],
                                                      camera_calibration["pp"])

    mask = cv2.imread(os.path.join(video_path, 'video_mask.png'), 0)

    vp1 = vp1[:-1] / vp1[-1]
    vp2 = vp2[:-1] / vp2[-1]
    vp3 = vp3[:-1] / vp3[-1]

    frame = np.zeros([1080, 1920])
    if pair == '12':
        M, IM = get_transform_matrix_with_criterion(vp1, vp2, mask, im_w, im_h)
    elif pair == '23':
        M, IM = get_transform_matrix_with_criterion(vp3, vp2, mask, im_w, im_h)

    vp1_t = np.array([vp1], dtype="float32")
    vp1_t = np.array([vp1_t])
    vp1_t = cv2.perspectiveTransform(vp1_t, M)
    vp1_t = vp1_t[0][0]

    tracker = Tracker(json_path, IM, vp1, vp2, vp3, vp1_t, im_w, im_h, name, threshold=threshold, fake=fake, write_name='640_360')
    tracker.read()

def test_dataset(images_path, ds_path, json_path, im_w, im_h):
    with open(ds_path, 'rb') as f:
        ds = pickle.load(f, encoding='latin-1', fix_imports=True)

    entry = ds[0]

    with open(json_path, 'r+') as file:
        # with open(os.path.join(os.path.dirname(json_path), 'system_retinanet_first.json'), 'r+') as file:
        structure = json.load(file)
        camera_calibration = structure['camera_calibration']

    vp1, vp2, vp3, _, _, _ = computeCameraCalibration(camera_calibration["vp1"], camera_calibration["vp2"],
                                                      camera_calibration["pp"])
    vp1 = vp1[:-1] / vp1[-1]
    vp2 = vp2[:-1] / vp2[-1]
    vp3 = vp3[:-1] / vp3[-1]

    frame = np.zeros((1080, 1920, 3))
    print(frame.shape)

    M, IM = get_transform_matrix(vp3, vp2, frame, im_w, im_h)

    vp1_t = np.array([vp1], dtype="float32")
    vp1_t = np.array([vp1_t])
    vp1_t = cv2.perspectiveTransform(vp1_t, M)
    vp1_t = vp1_t[0][0]

    tracker = Tracker(json_path, IM, vp1, vp2, vp3, vp1_t, im_w, im_h, 'none', threshold=0.2)

    pred_format = ['class_id', 'conf', 'x_min', 'y_min', 'x_max', 'y_max', 'centery']

    for entry in ds:
        frame = cv2.imread(os.path.join(images_path, entry['filename']))
        # frame = cv2.resize(frame,(1920,1080))
        # frame = cv2.warpPerspective(frame, IM, (1920, 1080))

        print(frame.shape)

        # t_image = cv2.warpPerspective(frame, M, (480, 300), borderMode=cv2.BORDER_REPLICATE)

        boxes = entry['labels']
        boxes = [[1 if elem == 'conf' else box[elem] for elem in pred_format] for box in boxes]
        boxes = np.array(boxes)
        print(boxes)

        image_b = tracker.process(boxes, cv2.warpPerspective(frame,IM,(1920,1080)))
        # image_b = decode_3dbb(boxes, frame, IM, vp0, vp1, vp2, vp0_t)

        cv2.imshow('frame', image_b)
        if cv2.waitKey(0) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":

    vid_path = 'D:/Skola/PhD/data/2016-ITS-BrnoCompSpeed/dataset'
    results_path = 'D:/Skola/PhD/data/2016-ITS-BrnoCompSpeed/results/'

    # vid_path = '/home/kocur/data/2016-ITS-BrnoCompSpeed/dataset/'
    # results_path = '/home/kocur/data/2016-ITS-BrnoCompSpeed/results/'

    vid_list = []
    calib_list = []
    for i in range(5, 7):
        # if i == 5:
        #     dir_list = ['session{}_center'.format(i), 'session{}_right'.format(i)]
        # else:
        dir_list = ['session{}_center'.format(i), 'session{}_left'.format(i), 'session{}_right'.format(i)]
        # dir_list = ['session{}_right'.format(i), 'session{}_left'.format(i),]
        # dir_list = ['session{}_left'.format(i)]
        vid_list.extend([os.path.join(vid_path, d) for d in dir_list])
        calib_list.extend([os.path.join(results_path, d, 'system_SochorCVIU_Edgelets_BBScale_Reg.json') for d in dir_list])
        # calib_list.extend([os.path.join(results_path, d, 'system_dubska_optimal_calib.json') for d in dir_list])
        # calib_list.extend([os.path.join(results_path, d, 'system_SochorCVIU_ManualCalib_ManualScale.json') for d in dir_list])
    name = '640_360_sochor'
    pair = '12'

    model = keras_retinanet.models.load_model('D:/Skola/PhD/code/keras-retinanet/models/valreg_640_360_12.h5',
                                              backbone_name='resnet50', convert=False)

    # model = keras_retinanet.models.load_model('/home/kocur/code/keras-retinanet/models/resnet50_640_360.h5',
    #                                           backbone_name='resnet50', convert=False)
    #
    print(model.summary)
    model._make_predict_function()
    #
    for vid, calib in zip(vid_list, calib_list):
        test_video(model, vid, calib, 640, 360, 12, name, pair, online=True) # out_path='D:/Skola/PhD/code/keras-retinanet/video_results/left_5.avi')

    # thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    # thresholds = [0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30]
    # thresholds = [0.2]

    # for calib in calib_list:
    #     for threshold in thresholds:
    #         track_detections(calib, vid, 640, 360, name, threshold, fake = True)


    # name = '640_360_late'
    #
    # for calib in calib_list:
    #     for threshold in thresholds:
    #         track_detections(calib, vid, 640, 360, name, threshold)

    # test_dataset('D:/Skola/PhD/data/BCS_boxed/images_0', 'D:/Skola/PhD/data/BCS_boxed/dataset_0.pkl',
    #              'D:/Skola/PhD/data/2016-ITS-BrnoCompSpeed/results/session0_center/system_dubska_optimal_calib.json',
    #              960, 540)
