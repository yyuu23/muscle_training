import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useLogin } from './useAuth';
import { AmbientBackground } from '../../components/AmbientBackground';

interface LoginFormData {
  email: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>();

  const onSubmit = async (data: LoginFormData) => {
    login.mutate({
      username: data.email,
      password: data.password,
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4 relative overflow-hidden">
      <AmbientBackground />
      {/* ambient brand glow */}
      <div
        className="absolute -top-32 left-1/2 -translate-x-1/2 w-[480px] h-[480px] rounded-full opacity-[0.14] blur-3xl pointer-events-none"
        style={{ background: 'radial-gradient(circle, var(--primary), transparent 70%)' }}
        aria-hidden
      />
      <div className="max-w-md w-full space-y-8 relative animate-slide-up">
        <div className="text-center">
          <div
            className="inline-flex w-16 h-16 rounded-3xl items-center justify-center mb-4 shadow-glow animate-scale-in"
            style={{ background: 'linear-gradient(135deg, var(--header-from), var(--header-to))' }}
          >
            {/* brand mark: dumbbell */}
            <svg viewBox="0 0 24 24" className="w-9 h-9" fill="none" aria-hidden>
              <path d="M4 9v6M7 7v10M17 7v10M20 9v6M7 12h10" stroke="var(--header-text)" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
          </div>
          <h2 className="text-3xl font-extrabold text-text tracking-tight">私人健身教练</h2>
          <p className="mt-2 text-sm text-text-secondary">登录到您的账户</p>
        </div>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)}>
          {login.error && (
            <div className="rounded-xl bg-danger-soft border border-danger/25 p-4 animate-scale-in">
              <p className="text-sm text-danger">{login.error.message}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-1.5">
                用户名 / 邮箱
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
              <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1.5">
                密码
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                className="input"
                {...register('password', {
                  required: '请输入密码',
                })}
              />
              {errors.password && (
                <p className="mt-1.5 text-sm text-danger">{errors.password.message}</p>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={login.isPending}
            className="btn btn-primary btn-lg w-full"
          >
            {login.isPending ? '登录中…' : '登录'}
          </button>

          <div className="text-center">
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="text-sm text-primary font-medium hover:underline underline-offset-4"
            >
              还没有账户？立即注册
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
