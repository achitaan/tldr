export async function getOpenCv() {
  const cv = await import("@techstark/opencv-js");
  window.cv = cv;
  return cv;
}