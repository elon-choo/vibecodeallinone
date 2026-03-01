# JWT Security Patterns

## Secure JWT Implementation

### Auth Module Setup

```typescript
// auth.module.ts
@Module({
  imports: [
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get<string>('JWT_ACCESS_SECRET'),
        signOptions: {
          expiresIn: '15m',  // 짧은 만료 시간
          algorithm: 'HS256',
        },
      }),
    }),
  ],
})
export class AuthModule {}
```

### Token Generation

```typescript
@Injectable()
export class AuthService {
  constructor(
    private jwtService: JwtService,
    private configService: ConfigService,
  ) {}

  // Access Token 생성
  generateAccessToken(user: User): string {
    const payload = {
      sub: user.id,
      email: user.email,
      role: user.role,
      type: 'access',
    };
    return this.jwtService.sign(payload);
  }

  // Refresh Token 생성 (다른 secret 사용)
  generateRefreshToken(user: User): string {
    const payload = {
      sub: user.id,
      type: 'refresh',
      tokenVersion: user.tokenVersion,
    };

    return this.jwtService.sign(payload, {
      secret: this.configService.get('JWT_REFRESH_SECRET'),
      expiresIn: '7d',
    });
  }

  // Token Refresh
  async refreshTokens(refreshToken: string): Promise<TokenPair> {
    try {
      const payload = this.jwtService.verify(refreshToken, {
        secret: this.configService.get('JWT_REFRESH_SECRET'),
      });

      const user = await this.usersService.findById(payload.sub);

      if (!user || user.tokenVersion !== payload.tokenVersion) {
        throw new UnauthorizedException('Invalid refresh token');
      }

      return {
        accessToken: this.generateAccessToken(user),
        refreshToken: this.generateRefreshToken(user),
      };
    } catch (error) {
      throw new UnauthorizedException('Invalid refresh token');
    }
  }

  // 로그아웃 (토큰 무효화)
  async logout(userId: string): Promise<void> {
    await this.usersService.incrementTokenVersion(userId);
  }
}
```

### JWT Strategy

```typescript
@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    configService: ConfigService,
    private usersService: UsersService,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: configService.get('JWT_ACCESS_SECRET'),
    });
  }

  async validate(payload: JwtPayload): Promise<User> {
    if (payload.type !== 'access') {
      throw new UnauthorizedException('Invalid token type');
    }

    const user = await this.usersService.findById(payload.sub);

    if (!user || !user.isActive) {
      throw new UnauthorizedException('User not found or inactive');
    }

    return user;
  }
}
```

## Cookie-based Token Storage

```typescript
@Controller('auth')
export class AuthController {
  @Post('login')
  async login(
    @Body() dto: LoginDto,
    @Res({ passthrough: true }) res: Response,
  ): Promise<{ accessToken: string }> {
    const { accessToken, refreshToken } = await this.authService.login(dto);

    // Refresh Token은 httpOnly 쿠키로 저장
    res.cookie('refreshToken', refreshToken, {
      httpOnly: true,        // JavaScript 접근 불가
      secure: true,          // HTTPS만
      sameSite: 'strict',    // CSRF 방지
      maxAge: 7 * 24 * 60 * 60 * 1000,  // 7일
      path: '/auth/refresh',
    });

    return { accessToken };
  }

  @Post('refresh')
  async refresh(
    @Req() req: Request,
    @Res({ passthrough: true }) res: Response,
  ): Promise<{ accessToken: string }> {
    const refreshToken = req.cookies['refreshToken'];

    if (!refreshToken) {
      throw new UnauthorizedException('Refresh token not found');
    }

    const { accessToken, refreshToken: newRefreshToken } =
      await this.authService.refreshTokens(refreshToken);

    // Refresh Token Rotation
    res.cookie('refreshToken', newRefreshToken, {
      httpOnly: true,
      secure: true,
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60 * 1000,
      path: '/auth/refresh',
    });

    return { accessToken };
  }

  @Post('logout')
  @UseGuards(JwtAuthGuard)
  async logout(
    @CurrentUser() user: User,
    @Res({ passthrough: true }) res: Response,
  ): Promise<void> {
    await this.authService.logout(user.id);

    res.clearCookie('refreshToken', {
      httpOnly: true,
      secure: true,
      sameSite: 'strict',
      path: '/auth/refresh',
    });
  }
}
```

## JWT Security Checklist

```markdown
- [ ] Access Token 만료 시간: 15분 이하
- [ ] Refresh Token 만료 시간: 7일 이하
- [ ] Access/Refresh Token에 다른 secret 사용
- [ ] Refresh Token은 httpOnly 쿠키로 저장
- [ ] Token에 type 필드로 용도 구분
- [ ] tokenVersion으로 토큰 무효화 지원
- [ ] Refresh Token Rotation 적용
- [ ] JWT secret은 환경변수로 관리
```
