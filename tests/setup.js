// Мок для window.webgazer
global.webgazer = {
  setRegression: () => webgazer,
  setTracker: () => webgazer,
  setGazeListener: () => webgazer,
  showPredictionPoints: () => webgazer,
  begin: () => Promise.resolve()
};

// Мок для window.faceapi
global.faceapi = {
  nets: {
    tinyFaceDetector: { loadFromUri: () => Promise.resolve() },
    faceLandmark68Net: { loadFromUri: () => Promise.resolve() },
    faceRecognitionNet: { loadFromUri: () => Promise.resolve() },
    faceExpressionNet: { loadFromUri: () => Promise.resolve() }
  },
  createCanvasFromMedia: () => ({
    width: 480,
    height: 360,
    getContext: () => ({
      clearRect: () => {}
    })
  }),
  matchDimensions: () => {},
  draw: {
    drawDetections: () => {},
    drawFaceLandmarks: () => {},
    drawFaceExpressions: () => {}
  }
};

// Глобальные функции из script.js
global.generateSessionId = () => 'session_test_123';
global.formatTime = (ms) => {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
};
global.getBrowserName = () => 'Chrome';
global.getBrowserVersion = () => '100';

// Мок для experimentData
global.experimentData = {
  tasks: [],
  gazeData: [],
  emotionData: [],
  currentTaskId: null
}; 