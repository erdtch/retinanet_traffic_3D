import json

import cv2
import numpy as np

from dataset_utils.warper import line, intersection, computeCameraCalibration, get_transform_matrix


def add_cross(image, center, color):
    thickness = 3
    size = 25
    image = cv2.rectangle(image, (int(center[0])-thickness,int(center[1])-size),(int(center[0])+thickness,int(center[1])+size), color, thickness=-1)
    image = cv2.rectangle(image, (int(center[0])-size,int(center[1])-thickness),(int(center[0])+size,int(center[1])+thickness), color, thickness=-1)
    return image


def base_image():
    image = np.zeros((4000, 4000, 3), np.uint8)
    image[:] = (255, 255, 255)

    image = cv2.rectangle(image, (680,820), (680+640,820+360), (200,200,200),thickness=-1)

    VP2 = (1020,2940)
    VP3 = (2950,765)

    for i in range(40):
        x = i*50
        y = 820
        p1 = (x,y)
        image = cv2.line(image, p1, VP2, (0, 0, 255), thickness=2, lineType=cv2.LINE_AA)

    for i in range(40):
        x = 680
        y = i * 50
        p1 = (x,y)
        image = cv2.line(image, p1, VP3, (255, 0, 0), thickness=2, lineType=cv2.LINE_AA)

    newimage = np.zeros((4000, 4000, 3), np.uint8)
    newimage[:] = (255, 255, 255)
    newimage[820:820+361,680:680+641] = image[820:820+361,680:680+641]
    image = newimage.copy()

    image = cv2.circle(image,VP2,60,(0,0,255),-1)
    image = cv2.circle(image,VP3,60,(255,0,0),-1)

    c1 = (680,820)
    c2 = (680+640,820)
    c3 = (680+640,820+360)
    c4 = (680,820+360)

    l1 = line(VP2,c4)
    l2 = line(VP2,c3)
    l3 = line(VP3,c1)
    l4 = line(VP3,c3)

    int1 = intersection(l1,l3)
    int2 = intersection(l1,l4)
    int3 = intersection(l2,l3)
    int4 = c3

    image = cv2.line(image, VP2, intersection(l1,line((0,0),(1,0))), (0,0,255), thickness=12, lineType=cv2.LINE_AA)
    image = cv2.line(image, VP2, intersection(l2,line((0,0),(1,0))), (0,0,255), thickness=12, lineType=cv2.LINE_AA)

    image = cv2.line(image, VP3, intersection(l3,line((0,0),(0,1))), (255,0,0), thickness=12, lineType=cv2.LINE_AA)
    image = cv2.line(image, VP3, intersection(l4,line((0,0),(0,1))), (255,0,0), thickness=12, lineType=cv2.LINE_AA)

    # image = add_cross(image, int1, (0,0,0))
    # image = add_cross(image, int2, (0,0,0))
    # image = add_cross(image, int3, (0,0,0))
    # image = add_cross(image, int4, (0,0,0))

    ipts = np.float32([int1, int2, int3, int4])
    cpts = np.float32([c1, c4, c2, c3])
    transform = cv2.getPerspectiveTransform(ipts, cpts)

    t_image = cv2.warpPerspective(newimage,transform,(4000,4000))
    t_image = cv2.rectangle(t_image,c1,c3,(0,0,0),thickness=2)

    cv2.imwrite('transform2.png', t_image)
    cv2.imwrite('transform1.png', image)

def generate_image():

    json_path = 'D:/Skola/PhD/data/2016-ITS-BrnoCompSpeed/results/session5_left/system_SochorCVIU_Edgelets_BBScale_Reg.json'


    with open(json_path, 'r+') as file:
        structure = json.load(file)
        camera_calibration = structure['camera_calibration']

    vp0, vp1, vp2, _, _, _ = computeCameraCalibration(camera_calibration["vp1"], camera_calibration["vp2"],
                                                      camera_calibration["pp"])
    vp0 = vp0[:-1] / vp0[-1]
    vp1 = vp1[:-1] / vp1[-1]
    vp2 = vp2[:-1] / vp2[-1]

    frame = np.zeros([1080, 1920])
    pts = [[100, 200], [1440, 200], [1440, 1080], [100, 1080]]
    # pts = None
    M, IM = get_transform_matrix(vp1, vp2, frame, 640, 360, inverse=True, pts=pts)

    M2, IM2 = get_transform_matrix(vp1, vp2, frame, 640, 360, inverse=True)

    image = cv2.imread('D:/Skola/PhD/data/2016-ITS-BrnoCompSpeed/dataset/session5_left/screen.png')

    t_image1 = cv2.warpPerspective(image, M, (640,360))
    t_image2 = cv2.warpPerspective(image, M2, (640,360))

    cv2.imwrite('cut.png', t_image1)
    cv2.imwrite('no-cut.png', t_image2)

def generate_image():

    json_path = 'D:/Skola/PhD/data/2016-ITS-BrnoCompSpeed/results/session5_left/system_SochorCVIU_Edgelets_BBScale_Reg.json'


    with open(json_path, 'r+') as file:
        structure = json.load(file)
        camera_calibration = structure['camera_calibration']

    vp0, vp1, vp2, _, _, _ = computeCameraCalibration(camera_calibration["vp1"], camera_calibration["vp2"],
                                                      camera_calibration["pp"])
    vp0 = vp0[:-1] / vp0[-1]
    vp1 = vp1[:-1] / vp1[-1]
    vp2 = vp2[:-1] / vp2[-1]

    frame = np.zeros([1080, 1920])
    pts = [[100, 200], [1440, 200], [1440, 1080], [100, 1080]]
    # pts = None
    M, IM = get_transform_matrix(vp1, vp2, frame, 640, 360, inverse=True, pts=pts)

    M2, IM2 = get_transform_matrix(vp1, vp2, frame, 640, 360, inverse=True)

    image = cv2.imread('D:/Skola/PhD/data/2016-ITS-BrnoCompSpeed/dataset/session5_left/screen.png')

    t_image1 = cv2.warpPerspective(image, M, (640,360))
    t_image2 = cv2.warpPerspective(image, M2, (640,360))

    cv2.imwrite('cut.png', t_image1)
    cv2.imwrite('no-cut.png', t_image2)

if __name__ == "__main__":
    generate_image()



