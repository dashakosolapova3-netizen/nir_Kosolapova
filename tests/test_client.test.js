// Используем Jest для тестирования

const {
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
} = require('../src/utils.js');

describe('Utility Functions', () => {
  test('generateSessionId creates valid ID', () => {
    const sessionId = generateSessionId();
    expect(sessionId).toMatch(/^session_\d+_[a-z0-9]+$/);
  });

  test('formatTime formats milliseconds correctly', () => {
    expect(formatTime(60000)).toBe('01:00');
    expect(formatTime(90000)).toBe('01:30');
    expect(formatTime(3600000)).toBe('60:00');
  });

  test('getBrowserName returns correct browser', () => {
    const browserName = getBrowserName();
    expect(['Chrome', 'Firefox', 'Safari', 'Edge', 'Unknown']).toContain(browserName);
  });
});

describe('Calibration Functions', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div class="calibrationDiv">
        <input type="button" class="Calibration" id="Pt1">
        <input type="button" class="Calibration" id="Pt2">
      </div>
      <canvas id="plotting_canvas"></canvas>
    `;
    window.CalibrationPoints = {};
    window.PointCalibrate = 0;
  });

  test('clearCalibration resets calibration state', () => {
    clearCalibration();
    const points = document.querySelectorAll('.Calibration');
    points.forEach(point => {
      expect(point.style.backgroundColor).toBe('red');
      expect(point.style.opacity).toBe('0.2');
      expect(point.hasAttribute('disabled')).toBeFalsy();
    });
    expect(window.CalibrationPoints).toEqual({});
    expect(window.PointCalibrate).toBe(0);
  });

  test('calPointClick updates point state correctly', () => {
    const point = document.getElementById('Pt1');
    calPointClick(point);
    expect(window.CalibrationPoints['Pt1']).toBe(1);
    expect(point.style.opacity).toBe('0.4');
  });
});

describe('Data Collection', () => {
  beforeEach(() => {
    experimentData.gazeData = [];
    experimentData.emotionData = [];
    experimentData.startTime = Date.now();
  });

  test('recordGazeData stores correct format', () => {
    const data = { x: 100, y: 200 };
    recordGazeData(data);
    const lastGazeData = experimentData.gazeData[experimentData.gazeData.length - 1];
    expect(lastGazeData).toHaveProperty('timestamp');
    expect(lastGazeData).toHaveProperty('x', 100);
    expect(lastGazeData).toHaveProperty('y', 200);
  });

  test('recordEmotionData processes expressions correctly', () => {
    const expressions = { happy: 0.8, sad: 0.2 };
    recordEmotionData(expressions);
    const lastEmotionData = experimentData.emotionData[experimentData.emotionData.length - 1];
    expect(lastEmotionData).toHaveProperty('timestamp');
    expect(lastEmotionData).toHaveProperty('expressions');
    expect(lastEmotionData.dominantEmotion).toBe('happy');
  });
});

describe('Experiment Control', () => {
  beforeEach(() => {
    experimentData.tasks = [];
    experimentData.currentTaskId = null;
  });

  test('startTask initializes task correctly', () => {
    const taskId = 'task_1';
    const description = 'Test Task';
    startTask(taskId, description);
    const task = experimentData.tasks[0];
    expect(task).toHaveProperty('id', taskId);
    expect(task).toHaveProperty('description', description);
    expect(task).toHaveProperty('startTime');
    expect(task.completed).toBe(false);
  });

  test('completeTask updates task state', () => {
    const taskId = 'task_1';
    startTask(taskId, 'Test Task');
    completeTask(taskId);
    const task = experimentData.tasks[0];
    expect(task.completed).toBe(true);
    expect(task).toHaveProperty('endTime');
    expect(task).toHaveProperty('duration');
  });
}); 