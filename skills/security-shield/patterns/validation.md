# Input Validation Patterns

## NestJS DTO Validation

### Basic DTO

```typescript
import {
  IsString,
  IsEmail,
  IsNotEmpty,
  MinLength,
  MaxLength,
  Matches,
  IsOptional,
  IsInt,
  Min,
  Max,
  IsEnum,
  IsUUID,
  ValidateNested,
  IsArray,
  ArrayMinSize,
  ArrayMaxSize,
} from 'class-validator';
import { Type, Transform } from 'class-transformer';

export class CreateUserDto {
  @IsEmail({}, { message: '유효한 이메일 형식이 아닙니다' })
  @MaxLength(255)
  @Transform(({ value }) => value?.toLowerCase().trim())
  email: string;

  @IsString()
  @IsNotEmpty({ message: '이름은 필수입니다' })
  @MinLength(1)
  @MaxLength(100)
  @Transform(({ value }) => value?.trim())
  name: string;

  @IsString()
  @MinLength(8, { message: '비밀번호는 최소 8자 이상이어야 합니다' })
  @MaxLength(72)  // bcrypt 제한
  @Matches(
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
    { message: '비밀번호는 대소문자, 숫자, 특수문자를 포함해야 합니다' }
  )
  password: string;

  @IsOptional()
  @IsEnum(['user', 'admin'], { message: '유효하지 않은 역할입니다' })
  role?: string = 'user';
}
```

### Nested Object Validation

```typescript
export class AddressDto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(200)
  street: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(100)
  city: string;

  @IsString()
  @Matches(/^\d{5}(-\d{4})?$/, { message: '유효한 우편번호 형식이 아닙니다' })
  zipCode: string;
}

export class CreateOrderDto {
  @ValidateNested()
  @Type(() => AddressDto)
  shippingAddress: AddressDto;

  @IsArray()
  @ArrayMinSize(1, { message: '최소 1개 이상의 상품이 필요합니다' })
  @ArrayMaxSize(100)
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];
}
```

### Query Parameter Validation

```typescript
export class PaginationQueryDto {
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number = 20;

  @IsOptional()
  @IsString()
  @IsEnum(['createdAt', 'name', 'email'])
  sortBy?: string = 'createdAt';

  @IsOptional()
  @IsEnum(['ASC', 'DESC'])
  sortOrder?: 'ASC' | 'DESC' = 'DESC';
}
```

### Custom Validator

```typescript
import {
  registerDecorator,
  ValidationOptions,
  ValidatorConstraint,
  ValidatorConstraintInterface,
} from 'class-validator';

@ValidatorConstraint({ async: false })
export class IsNotCommonPasswordConstraint implements ValidatorConstraintInterface {
  private commonPasswords = [
    'password', '123456', 'qwerty', 'abc123', 'password123',
    'admin', 'letmein', 'welcome', 'monkey', 'dragon',
  ];

  validate(password: string): boolean {
    return !this.commonPasswords.includes(password?.toLowerCase());
  }

  defaultMessage(): string {
    return '너무 일반적인 비밀번호입니다. 더 복잡한 비밀번호를 사용하세요.';
  }
}

export function IsNotCommonPassword(validationOptions?: ValidationOptions) {
  return function (object: object, propertyName: string) {
    registerDecorator({
      target: object.constructor,
      propertyName: propertyName,
      options: validationOptions,
      constraints: [],
      validator: IsNotCommonPasswordConstraint,
    });
  };
}
```

## Frontend Validation (Zod)

```typescript
import { z } from 'zod';

export const emailSchema = z
  .string()
  .email('유효한 이메일 형식이 아닙니다')
  .max(255)
  .transform(val => val.toLowerCase().trim());

export const passwordSchema = z
  .string()
  .min(8, '비밀번호는 최소 8자 이상이어야 합니다')
  .max(72)
  .regex(
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/,
    '비밀번호는 대소문자, 숫자, 특수문자를 포함해야 합니다'
  );

export const createUserSchema = z.object({
  email: emailSchema,
  name: z.string().min(1).max(100).transform(val => val.trim()),
  password: passwordSchema,
  confirmPassword: z.string(),
}).refine(data => data.password === data.confirmPassword, {
  message: '비밀번호가 일치하지 않습니다',
  path: ['confirmPassword'],
});

// 사용
async function handleUserCreation(rawData: unknown) {
  const result = createUserSchema.safeParse(rawData);

  if (!result.success) {
    const errors = result.error.errors.map(e => ({
      field: e.path.join('.'),
      message: e.message,
    }));
    throw new ValidationError(errors);
  }

  await createUser(result.data);
}
```

## File Upload Validation

```typescript
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

export const imageFileFilter = (
  req: Request,
  file: Express.Multer.File,
  callback: (error: Error | null, acceptFile: boolean) => void
) => {
  // MIME 타입 검증
  if (!ALLOWED_IMAGE_TYPES.includes(file.mimetype)) {
    return callback(
      new BadRequestException('허용되지 않는 파일 형식입니다'),
      false
    );
  }

  // 확장자 검증
  const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
  const fileExt = extname(file.originalname).toLowerCase();

  if (!allowedExtensions.includes(fileExt)) {
    return callback(
      new BadRequestException('허용되지 않는 파일 확장자입니다'),
      false
    );
  }

  callback(null, true);
};

// Magic Bytes 검증
private async validateImageMagicBytes(filePath: string): Promise<boolean> {
  const buffer = Buffer.alloc(8);
  const fd = await fs.open(filePath, 'r');
  await fd.read(buffer, 0, 8, 0);
  await fd.close();

  const signatures = {
    jpeg: [0xff, 0xd8, 0xff],
    png: [0x89, 0x50, 0x4e, 0x47],
    gif: [0x47, 0x49, 0x46],
    webp: [0x52, 0x49, 0x46, 0x46],
  };

  for (const sig of Object.values(signatures)) {
    if (sig.every((byte, i) => buffer[i] === byte)) {
      return true;
    }
  }

  return false;
}
```
