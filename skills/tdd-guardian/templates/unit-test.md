# Unit Test Templates

## NestJS Service Unit Test Template

```typescript
// ═══════════════════════════════════════════════════════════════
// NestJS Service Unit Test Template
// File: src/users/users.service.spec.ts
// ═══════════════════════════════════════════════════════════════

import { Test, TestingModule } from '@nestjs/testing';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { UsersService } from './users.service';
import { User } from './entities/user.entity';
import { CreateUserDto } from './dto/create-user.dto';
import { ConflictException, NotFoundException } from '@nestjs/common';

describe('UsersService', () => {
  let service: UsersService;
  let repository: jest.Mocked<Repository<User>>;

  // ─────────────────────────────────────────────────────────────
  // Test Setup
  // ─────────────────────────────────────────────────────────────

  beforeEach(async () => {
    const mockRepository = {
      find: jest.fn(),
      findOne: jest.fn(),
      save: jest.fn(),
      delete: jest.fn(),
      create: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UsersService,
        {
          provide: getRepositoryToken(User),
          useValue: mockRepository,
        },
      ],
    }).compile();

    service = module.get<UsersService>(UsersService);
    repository = module.get(getRepositoryToken(User));
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  // ─────────────────────────────────────────────────────────────
  // create() Tests
  // ─────────────────────────────────────────────────────────────

  describe('create()', () => {
    const createUserDto: CreateUserDto = {
      email: 'test@test.com',
      name: 'Test User',
      password: 'Test1234!',
    };

    const mockUser: User = {
      id: 'uuid-1234',
      email: 'test@test.com',
      name: 'Test User',
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-01'),
    };

    // Happy Path
    it('should create a user with valid data', async () => {
      // Arrange
      repository.findOne.mockResolvedValue(null);
      repository.create.mockReturnValue(mockUser);
      repository.save.mockResolvedValue(mockUser);

      // Act
      const result = await service.create(createUserDto);

      // Assert
      expect(result).toEqual(mockUser);
      expect(result.id).toMatch(/^[a-f0-9-]{36}$|^uuid-/);
      expect(result.email).toBe('test@test.com');
      expect(result.name).toBe('Test User');
      expect(repository.findOne).toHaveBeenCalledWith({
        where: { email: createUserDto.email }
      });
      expect(repository.save).toHaveBeenCalledTimes(1);
    });

    // Error Path: Duplicate Email
    it('should throw ConflictException for duplicate email', async () => {
      // Arrange
      repository.findOne.mockResolvedValue(mockUser);

      // Act & Assert
      await expect(service.create(createUserDto))
        .rejects
        .toThrow(ConflictException);

      await expect(service.create(createUserDto))
        .rejects
        .toMatchObject({
          message: expect.stringContaining('already exists')
        });

      expect(repository.save).not.toHaveBeenCalled();
    });

    // Error Path: Database Error
    it('should propagate database errors', async () => {
      // Arrange
      repository.findOne.mockResolvedValue(null);
      repository.save.mockRejectedValue(new Error('Database connection lost'));

      // Act & Assert
      await expect(service.create(createUserDto))
        .rejects
        .toThrow('Database connection lost');
    });

    // Boundary: Minimum Name Length
    it('should accept minimum name length (1 char)', async () => {
      const minNameDto = { ...createUserDto, name: 'A' };
      repository.findOne.mockResolvedValue(null);
      repository.create.mockReturnValue({ ...mockUser, name: 'A' });
      repository.save.mockResolvedValue({ ...mockUser, name: 'A' });

      const result = await service.create(minNameDto);

      expect(result.name).toBe('A');
    });
  });

  // ─────────────────────────────────────────────────────────────
  // findById() Tests
  // ─────────────────────────────────────────────────────────────

  describe('findById()', () => {
    const mockUser: User = {
      id: 'uuid-1234',
      email: 'test@test.com',
      name: 'Test User',
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-01'),
    };

    // Happy Path
    it('should return user when found', async () => {
      repository.findOne.mockResolvedValue(mockUser);

      const result = await service.findById('uuid-1234');

      expect(result).toEqual(mockUser);
      expect(result.id).toBe('uuid-1234');
      expect(repository.findOne).toHaveBeenCalledWith({
        where: { id: 'uuid-1234' }
      });
    });

    // Error Path: Not Found
    it('should throw NotFoundException when user not found', async () => {
      repository.findOne.mockResolvedValue(null);

      await expect(service.findById('non-existent-id'))
        .rejects
        .toThrow(NotFoundException);

      await expect(service.findById('non-existent-id'))
        .rejects
        .toMatchObject({
          message: expect.stringContaining('not found')
        });
    });
  });
});
```

## NestJS Controller Unit Test Template

```typescript
// ═══════════════════════════════════════════════════════════════
// NestJS Controller Unit Test Template
// File: src/users/users.controller.spec.ts
// ═══════════════════════════════════════════════════════════════

import { Test, TestingModule } from '@nestjs/testing';
import { UsersController } from './users.controller';
import { UsersService } from './users.service';
import { CreateUserDto } from './dto/create-user.dto';
import { User } from './entities/user.entity';
import { ConflictException, NotFoundException } from '@nestjs/common';

describe('UsersController', () => {
  let controller: UsersController;
  let service: jest.Mocked<UsersService>;

  beforeEach(async () => {
    const mockService = {
      create: jest.fn(),
      findAll: jest.fn(),
      findById: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      controllers: [UsersController],
      providers: [
        {
          provide: UsersService,
          useValue: mockService,
        },
      ],
    }).compile();

    controller = module.get<UsersController>(UsersController);
    service = module.get(UsersService);
  });

  describe('POST /users (create)', () => {
    const createUserDto: CreateUserDto = {
      email: 'test@test.com',
      name: 'Test User',
      password: 'Test1234!',
    };

    const mockUser: User = {
      id: 'uuid-1234',
      email: 'test@test.com',
      name: 'Test User',
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    it('should create user and return 201', async () => {
      service.create.mockResolvedValue(mockUser);

      const result = await controller.create(createUserDto);

      expect(result).toEqual(mockUser);
      expect(service.create).toHaveBeenCalledWith(createUserDto);
    });

    it('should propagate ConflictException for duplicate', async () => {
      service.create.mockRejectedValue(
        new ConflictException('Email already exists')
      );

      await expect(controller.create(createUserDto))
        .rejects
        .toThrow(ConflictException);
    });
  });

  describe('GET /users/:id (findById)', () => {
    const mockUser: User = {
      id: 'uuid-1234',
      email: 'test@test.com',
      name: 'Test User',
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    it('should return user when found', async () => {
      service.findById.mockResolvedValue(mockUser);

      const result = await controller.findById('uuid-1234');

      expect(result).toEqual(mockUser);
      expect(result.id).toBe('uuid-1234');
    });

    it('should propagate NotFoundException', async () => {
      service.findById.mockRejectedValue(
        new NotFoundException('User not found')
      );

      await expect(controller.findById('non-existent'))
        .rejects
        .toThrow(NotFoundException);
    });
  });
});
```
