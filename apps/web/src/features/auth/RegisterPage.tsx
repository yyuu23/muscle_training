import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useRegister } from './useAuth';

interface RegisterFormData {
  email: string;
  displayName: string;
  password: string;
  confirmPassword: string;
  inviteCode: string;
}

export function RegisterPage() {
  const navigate = useNavigate();
  const register_mutation = useRegister();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>();

  const password = watch('password');

  const onSubmit = async (data: RegisterFormData) => {
    register_mutation.mutate({
      username: data.email,
      display_name: data.displayName,
      password: data.password,
      invite_code: data.inviteCode,
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            创建账户
          </h2>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          {register_mutation.error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{register_mutation.error.message}</div>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                邮箱
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className="input-field mt-1"
                {...register('email', {
                  required: '请输入邮箱',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: '邮箱格式不正确',
                  },
                })}
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="displayName" className="block text-sm font-medium text-gray-700">
                显示名称
              </label>
              <input
                id="displayName"
                type="text"
                autoComplete="name"
                className="input-field mt-1"
                placeholder="输入您的昵称"
                {...register('displayName', {
                  required: '请输入显示名称',
                  minLength: {
                    value: 1,
                    message: '显示名称至少1个字符',
                  },
                  maxLength: {
                    value: 100,
                    message: '显示名称最多100个字符',
                  },
                })}
              />
              {errors.displayName && (
                <p className="mt-1 text-sm text-red-600">{errors.displayName.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                密码
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                className="input-field mt-1"
                {...register('password', {
                  required: '请输入密码',
                  minLength: {
                    value: 12,
                    message: '密码至少12个字符',
                  },
                  pattern: {
                    value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]/,
                    message: '密码需包含大小写字母、数字和特殊字符',
                  },
                })}
              />
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                至少12个字符，包含大小写字母、数字和特殊字符
              </p>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                确认密码
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                className="input-field mt-1"
                {...register('confirmPassword', {
                  required: '请确认密码',
                  validate: (value) => value === password || '两次密码不一致',
                })}
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-600">{errors.confirmPassword.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="inviteCode" className="block text-sm font-medium text-gray-700">
                邀请码
              </label>
              <input
                id="inviteCode"
                type="text"
                className="input-field mt-1"
                placeholder="输入邀请码"
                {...register('inviteCode', {
                  required: '请输入邀请码',
                })}
              />
              {errors.inviteCode && (
                <p className="mt-1 text-sm text-red-600">{errors.inviteCode.message}</p>
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={register_mutation.isPending}
              className="btn-primary w-full"
            >
              {register_mutation.isPending ? '注册中...' : '注册'}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="text-sm text-blue-600 hover:text-blue-500"
            >
              已有账户？立即登录
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
