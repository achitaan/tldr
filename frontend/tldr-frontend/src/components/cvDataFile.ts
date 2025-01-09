import { getOpenCv } from "./loader";

export async function loadDataFile(cvFilePath : string, url :string) {
  const cv = await getOpenCv();
  // see https://docs.opencv.org/master/utils.js
  const response = await fetch(url);
  const buffer = await response.arrayBuffer();
  const data = new Uint8Array(buffer);
  cv.FS_createDataFile("/", cvFilePath, data, true, false, false);
}
