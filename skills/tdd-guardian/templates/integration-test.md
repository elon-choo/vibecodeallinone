# Integration Test Template

## NestJS E2E Test Template

```typescript
// ═══════════════════════════════════════════════════════════════
// Integration Test Template
// File: test/users.e2e-spec.ts
// ═══════════════════════════════════════════════════════════════

import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../src/app.module';
import { DataSource } from 'typeorm';

describe('Users API (e2e)', () => {
  let app: INestApplication;
  let dataSource: DataSource;

  // ─────────────────────────────────────────────────────────────
  // Test Setup
  // ─────────────────────────────────────────────────────────────

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    app.useGlobalPipes(new ValidationPipe({
      whitelist: true,
      transform: true,
    }));

    await app.init();

    dataSource = moduleFixture.get<DataSource>(DataSource);
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    // Clean database before each test
    await dataSource.query('DELETE FROM users');
  });

  // ─────────────────────────────────────────────────────────────
  // POST /users Tests
  // ─────────────────────────────────────────────────────────────

  describe('POST /users', () => {
    const validUser = {
      email: 'test@test.com',
      name: 'Test User',
      password: 'Password123!',
    };

    // Happy Path
    it('should create user with valid data (201)', async () => {
      const response = await request(app.getHttpServer())
        .post('/users')
        .send(validUser)
        .expect(201);

      expect(response.body).toMatchObject({
        id: expect.any(String),
        email: 'test@test.com',
        name: 'Test User',
        createdAt: expect.any(String),
      });

      // Password should not be in response
      expect(response.body.password).toBeUndefined();
    });

    // Validation Error
    it('should reject invalid email (400)', async () => {
      const response = await request(app.getHttpServer())
        .post('/users')
        .send({ ...validUser, email: 'invalid-email' })
        .expect(400);

      expect(response.body.message).toContain('email');
    });

    // Duplicate Error
    it('should reject duplicate email (409)', async () => {
      // Create first user
      await request(app.getHttpServer())
        .post('/users')
        .send(validUser)
        .expect(201);

      // Try to create duplicate
      const response = await request(app.getHttpServer())
        .post('/users')
        .send(validUser)
        .expect(409);

      expect(response.body.message).toContain('already exists');
    });

    // Missing Required Field
    it('should reject missing name (400)', async () => {
      const { name, ...userWithoutName } = validUser;

      const response = await request(app.getHttpServer())
        .post('/users')
        .send(userWithoutName)
        .expect(400);

      expect(response.body.message).toContain('name');
    });
  });

  // ─────────────────────────────────────────────────────────────
  // GET /users/:id Tests
  // ─────────────────────────────────────────────────────────────

  describe('GET /users/:id', () => {
    let createdUserId: string;

    beforeEach(async () => {
      const response = await request(app.getHttpServer())
        .post('/users')
        .send({
          email: 'test@test.com',
          name: 'Test User',
          password: 'Password123!',
        });
      createdUserId = response.body.id;
    });

    // Happy Path
    it('should return user when found (200)', async () => {
      const response = await request(app.getHttpServer())
        .get(`/users/${createdUserId}`)
        .expect(200);

      expect(response.body).toMatchObject({
        id: createdUserId,
        email: 'test@test.com',
        name: 'Test User',
      });
    });

    // Not Found
    it('should return 404 for non-existent user', async () => {
      const response = await request(app.getHttpServer())
        .get('/users/non-existent-id')
        .expect(404);

      expect(response.body.message).toContain('not found');
    });
  });

  // ─────────────────────────────────────────────────────────────
  // Full Flow Test
  // ─────────────────────────────────────────────────────────────

  describe('Full CRUD Flow', () => {
    it('should complete full user lifecycle', async () => {
      // 1. Create
      const createResponse = await request(app.getHttpServer())
        .post('/users')
        .send({
          email: 'lifecycle@test.com',
          name: 'Lifecycle User',
          password: 'Password123!',
        })
        .expect(201);

      const userId = createResponse.body.id;

      // 2. Read
      const readResponse = await request(app.getHttpServer())
        .get(`/users/${userId}`)
        .expect(200);

      expect(readResponse.body.name).toBe('Lifecycle User');

      // 3. Update
      const updateResponse = await request(app.getHttpServer())
        .patch(`/users/${userId}`)
        .send({ name: 'Updated Name' })
        .expect(200);

      expect(updateResponse.body.name).toBe('Updated Name');

      // 4. Delete
      await request(app.getHttpServer())
        .delete(`/users/${userId}`)
        .expect(204);

      // 5. Verify Deleted
      await request(app.getHttpServer())
        .get(`/users/${userId}`)
        .expect(404);
    });
  });
});
```

## API Test with Authentication

```typescript
// ═══════════════════════════════════════════════════════════════
// Authenticated API Test Template
// ═══════════════════════════════════════════════════════════════

describe('Protected Routes (e2e)', () => {
  let app: INestApplication;
  let authToken: string;

  beforeAll(async () => {
    // ... app setup ...

    // Login to get auth token
    const loginResponse = await request(app.getHttpServer())
      .post('/auth/login')
      .send({
        email: 'admin@test.com',
        password: 'AdminPass123!',
      });

    authToken = loginResponse.body.accessToken;
  });

  describe('GET /users (protected)', () => {
    it('should return 401 without token', async () => {
      await request(app.getHttpServer())
        .get('/users')
        .expect(401);
    });

    it('should return 401 with invalid token', async () => {
      await request(app.getHttpServer())
        .get('/users')
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);
    });

    it('should return users with valid token', async () => {
      const response = await request(app.getHttpServer())
        .get('/users')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(Array.isArray(response.body)).toBe(true);
    });
  });
});
```
