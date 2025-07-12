const request = require('supertest');
const app = require('./server'); // Adjust the path as necessary

describe('GET /hello', () => {
  it('should return a Hello World message', async () => {
    const response = await request(app).get('/hello');
    expect(response.statusCode).toBe(200);
    expect(response.body).toEqual({ message: 'Hello World' });
  });
});