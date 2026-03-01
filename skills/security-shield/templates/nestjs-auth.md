# NestJS Authentication Template

## Secure Controller Template

```typescript
import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  Param,
  Query,
  UseGuards,
  UseInterceptors,
  ParseUUIDPipe,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth, ApiResponse } from '@nestjs/swagger';
import { Throttle, ThrottlerGuard } from '@nestjs/throttler';

@Controller('users')
@ApiTags('Users')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard, ThrottlerGuard)
@UseInterceptors(LoggingInterceptor)
export class UsersController {
  constructor(
    private readonly usersService: UsersService,
    private readonly auditService: AuditService,
  ) {}

  @Get()
  @Roles('admin')
  @UseGuards(RolesGuard)
  @ApiOperation({ summary: '모든 사용자 조회 (관리자)' })
  async findAll(
    @Query() query: PaginationQueryDto,
    @CurrentUser() currentUser: User,
  ): Promise<PaginatedResponse<UserResponseDto>> {
    await this.auditService.log({
      action: 'users.findAll',
      actor: currentUser.id,
      details: { query },
    });

    return this.usersService.findAll(query);
  }

  @Get(':id')
  @ApiOperation({ summary: '사용자 조회' })
  async findById(
    @Param('id', ParseUUIDPipe) id: string,
    @CurrentUser() currentUser: User,
  ): Promise<UserResponseDto> {
    // 소유권 검증
    if (currentUser.id !== id && currentUser.role !== 'admin') {
      throw new ForbiddenException('다른 사용자 정보에 접근할 수 없습니다');
    }

    const user = await this.usersService.findById(id);

    if (!user) {
      throw new NotFoundException('사용자를 찾을 수 없습니다');
    }

    return new UserResponseDto(user);
  }

  @Post()
  @Public()
  @Throttle(3, 60)
  @HttpCode(HttpStatus.CREATED)
  @ApiOperation({ summary: '사용자 생성 (회원가입)' })
  async create(
    @Body() dto: CreateUserDto,
  ): Promise<UserResponseDto> {
    const user = await this.usersService.create(dto);

    await this.auditService.log({
      action: 'users.create',
      details: { userId: user.id, email: user.email },
    });

    return new UserResponseDto(user);
  }

  @Put(':id')
  async update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() dto: UpdateUserDto,
    @CurrentUser() currentUser: User,
  ): Promise<UserResponseDto> {
    if (currentUser.id !== id && currentUser.role !== 'admin') {
      throw new ForbiddenException('다른 사용자 정보를 수정할 수 없습니다');
    }

    const user = await this.usersService.update(id, dto);

    await this.auditService.log({
      action: 'users.update',
      actor: currentUser.id,
      target: id,
      details: { fields: Object.keys(dto) },
    });

    return new UserResponseDto(user);
  }

  @Delete(':id')
  @Roles('admin')
  @UseGuards(RolesGuard)
  @HttpCode(HttpStatus.NO_CONTENT)
  async delete(
    @Param('id', ParseUUIDPipe) id: string,
    @CurrentUser() currentUser: User,
  ): Promise<void> {
    if (currentUser.id === id) {
      throw new ForbiddenException('자기 자신은 삭제할 수 없습니다');
    }

    await this.usersService.delete(id);

    await this.auditService.log({
      action: 'users.delete',
      actor: currentUser.id,
      target: id,
    });
  }
}
```

## Secure Response DTO

```typescript
import { Exclude, Expose, Transform } from 'class-transformer';

export class UserResponseDto {
  @Expose()
  id: string;

  @Expose()
  email: string;

  @Expose()
  name: string;

  @Expose()
  role: string;

  @Expose()
  createdAt: Date;

  // 민감 정보 제외
  @Exclude()
  password: string;

  @Exclude()
  tokenVersion: number;

  @Exclude()
  isDeleted: boolean;

  @Expose()
  @Transform(({ value }) => value?.toISOString())
  lastLoginAt: Date;

  constructor(partial: Partial<UserResponseDto>) {
    Object.assign(this, partial);
  }
}
```

## Rate Limiting Setup

```typescript
// app.module.ts
import { ThrottlerModule } from '@nestjs/throttler';

@Module({
  imports: [
    ThrottlerModule.forRoot({
      ttl: 60,    // 60초
      limit: 10,  // 10회
    }),
  ],
})
export class AppModule {}

// Controller에서 커스텀 제한
@Post('login')
@Throttle(5, 300)  // 5분에 5회 (로그인은 더 엄격하게)
async login(@Body() dto: LoginDto) {}
```

## Security Headers (Helmet)

```typescript
// main.ts
import helmet from 'helmet';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:', 'https:'],
        connectSrc: ["'self'"],
        fontSrc: ["'self'"],
        objectSrc: ["'none'"],
        mediaSrc: ["'self'"],
        frameSrc: ["'none'"],
      },
    },
    xssFilter: true,
  }));

  await app.listen(3000);
}
```

## Error Handling (No Stack Trace)

```typescript
// all-exceptions.filter.ts
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    const status = exception instanceof HttpException
      ? exception.getStatus()
      : HttpStatus.INTERNAL_SERVER_ERROR;

    const message = exception instanceof HttpException
      ? exception.message
      : 'Internal server error';

    // 프로덕션에서 스택 트레이스 숨김
    response.status(status).json({
      statusCode: status,
      message,
      timestamp: new Date().toISOString(),
      // stack: exception.stack  // 절대 노출하지 않음!
    });
  }
}
```
