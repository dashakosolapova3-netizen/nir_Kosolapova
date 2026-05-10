// Утилитные функции
function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function formatTime(ms) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function getBrowserName() {
  if (typeof navigator === 'undefined') return 'Unknown';
  const userAgent = navigator.userAgent;
  if (userAgent.includes('Firefox')) return 'Firefox';
  if (userAgent.includes('Chrome')) return 'Chrome';
  if (userAgent.includes('Safari')) return 'Safari';
  if (userAgent.includes('Edge')) return 'Edge';
  return 'Unknown';
}

// Функции калибровки
function clearCalibration() {
  if (typeof document === 'undefined') return;
  document.querySelectorAll('.Calibration').forEach(point => {
    point.style.backgroundColor = 'red';
    point.style.opacity = '0.2';
    point.removeAttribute('disabled');
  });
  window.CalibrationPoints = {};
  window.PointCalibrate = 0;
}

function calPointClick(node) {
  if (!node || typeof document === 'undefined') return;
  const id = node.id;
  if (!window.CalibrationPoints) window.CalibrationPoints = {};
  if (!window.CalibrationPoints[id]) window.CalibrationPoints[id] = 0;
  window.CalibrationPoints[id]++;
  node.style.opacity = 0.2 * window.CalibrationPoints[id] + 0.2;
}

// Функции сбора данных
let experimentData = {
  tasks: [],
  gazeData: [],
  emotionData: [],
  currentTaskId: null
};

function recordGazeData(data) {
  experimentData.gazeData.push({
    timestamp: Date.now(),
    taskId: experimentData.currentTaskId,
    x: data.x,
    y: data.y,
    relativeTime: Date.now() - (experimentData.startTime || Date.now())
  });
}

function recordEmotionData(expressions) {
  experimentData.emotionData.push({
    timestamp: Date.now(),
    taskId: experimentData.currentTaskId,
    expressions: expressions,
    relativeTime: Date.now() - (experimentData.startTime || Date.now()),
    dominantEmotion: Object.entries(expressions).reduce((a, b) => a[1] > b[1] ? a : b)[0]
  });
}

// Функции управления экспериментом
function startTask(taskId, taskDescription) {
  const task = {
    id: taskId,
    description: taskDescription,
    startTime: Date.now(),
    endTime: null,
    duration: null,
    completed: false
  };
  experimentData.tasks.push(task);
  experimentData.currentTaskId = taskId;
  return task;
}

function completeTask(taskId) {
  const task = experimentData.tasks.find(t => t.id === taskId);
  if (task) {
    task.endTime = Date.now();
    task.duration = task.endTime - task.startTime;
    task.completed = true;
  }
  experimentData.currentTaskId = null;
  return task;
}

module.exports = {
  generateSessionId,
  formatTime,
  getBrowserName,
  clearCalibration,
  calPointClick,
  recordGazeData,
  recordEmotionData,
  startTask,
  completeTask,
  experimentData
}; 