"""Standard document clean-up before classic OCR: find the paper, flatten the
perspective, even out the light. Gemini gets the original photo."""
import cv2
import numpy as np


def order_corners(pts):
    pts = pts.reshape(4, 2).astype(np.float32)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def flatten_document(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img
    page = max(contours, key=cv2.contourArea)
    if cv2.contourArea(page) < 0.2 * img.shape[0] * img.shape[1]:
        return img
    quad = cv2.approxPolyDP(page, 0.02 * cv2.arcLength(page, True), True)
    if len(quad) != 4:
        quad = cv2.boxPoints(cv2.minAreaRect(page))
    tl, tr, br, bl = order_corners(quad)
    w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    m = cv2.getPerspectiveTransform(np.float32([tl, tr, br, bl]), np.float32([[0, 0], [w, 0], [w, h], [0, h]]))
    return cv2.warpPerspective(img, m, (w, h))


def even_light(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def prepare(src_path, dst_path):
    img = cv2.imread(str(src_path))
    out = even_light(flatten_document(img))
    cv2.imwrite(str(dst_path), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
