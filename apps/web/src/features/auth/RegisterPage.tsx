import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useRegister } from './useAuth';
import { AmbientBackground } from '../../components/AmbientBackground';

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
    <div className="min-h-screen flex items-center justify-center bg-bg px-4 py-10 relative overflow-hidden">
      <AmbientBackground />
      <div
        className="absolute -top-32 left-1/2 -translate-x-1/2 w-[480px] h-[480px] rounded-full opacity-[0.14] blur-3xl pointer-events-none"
        style={{ background: 'radial-gradient(circle, var(--primary), transparent 70%)' }}
        aria-hidden
      />
      <div className="max-w-md w-full space-y-6 relative animate-slide-up">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-text tracking-tight">创建账户</h2>
          <p className="mt-2 text-sm text-text-secondary">凭邀请码注册，仅限受邀用户</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          {register_mutation.error && (
            <div className="rounded-xl bg-danger-soft border border-danger/25 p-4 animate-scale-in">
              <p className="text-sm text-danger">{register_mutation.error.message}</p>
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-1.5">
              邮箱
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="input"
              {...register('email', {
                required: '请输入邮箱',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: '邮箱格式不正确',
                },
              })}
            />
            {errors.email && (
              <p className="mt-1.5 text-sm text-danger">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="displayName" className="block text-sm font-medium text-text-secondary mb-1.5">
              显示名称
            </label>
            <input
              id="displayName"
              type="text"
              autoComplete="name"
              className="input"
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
              <p className="mt-1.5 text-sm text-danger">{errors.displayName.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1.5">
              密码
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              className="input"
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
              <p className="mt-1.5 text-sm text-danger">{errors.password.message}</p>
            )}
            <p className="mt-1.5 text-xs text-text-muted">
              至少12个字符，包含大小写字母、数字和特殊字符
            </p>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-text-secondary mb-1.5">
              确认密码
            </label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              className="input"
              {...register('confirmPassword', {
                required: '请确认密码',
                validate: (value) => value === password || '两次密码不一致',
              })}
            />
            {errors.confirmPassword && (
              <p className="mt-1.5 text-sm text-danger">{errors.confirmPassword.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="inviteCode" className="block text-sm font-medium text-text-secondary mb-1.5">
              邀请码
            </label>
            <input
              id="inviteCode"
              type="text"
              className="input"
              placeholder="输入邀请码"
              {...register('inviteCode', {
                required: '请输入邀请码',
              })}
            />
            {errors.inviteCode && (
              <p className="mt-1.5 text-sm text-danger">{errors.inviteCode.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={register_mutation.isPending}
            className="btn btn-primary btn-lg w-full !mt-6"
          >
            {register_mutation.isPending ? '注册中…' : '注册'}
          </button>

          <div className="text-center">
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="text-sm text-primary font-medium hover:underline underline-offset-4"
            >
              已有账户？立即登录
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
