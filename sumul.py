import random
import matplotlib.pyplot as plt

def simulate_random_fibonacci(N, trials=1, seed=None):
    """
    Random Fibonacci 수열을 시뮬레이션하고 a_n = |x_n|^{1/n}을 계산합니다.

    Parameters:
    - N: 생성할 항의 수.
    - trials: 평균을 내기 위한 독립적인 시뮬레이션 횟수.
    - seed: 재현성을 위한 랜덤 시드.

    Returns:
    - 평균된 a_n 값들의 리스트.
    """
    if seed is not None:
        random.seed(seed)
    
    # 시뮬레이션 횟수만큼 a_n의 합을 저장할 리스트 초기화
    a_n_sum = [0.0 for _ in range(N+1)]
    
    for t in range(trials):
        # 시퀀스 초기화
        x = [1, 1]  # x0 = x1 = 1
        
        # N번째 항까지 시퀀스 생성
        for n in range(N):
            # x_{n+1}과 x_n의 부호를 랜덤하게 선택
            s1 = random.choice([1, -1])
            s2 = random.choice([1, -1])
            next_x = s1 * x[-1] + s2 * x[-2]
            x.append(next_x)
        
        # 이 시도에서의 a_n 계산
        for n in range(1, N+1):
            if x[n] != 0:
                a_n = abs(x[n]) ** (1/n)
            else:
                # x_n = 0인 경우 a_n을 0으로 설정
                a_n = 0
            a_n_sum[n] += a_n
    
    # 시뮬레이션 횟수로 나누어 평균 a_n 계산
    a_n_avg = [a_n_sum[n] / trials for n in range(N+1)]
    
    return a_n_avg

# 파라미터 설정
N = 100          # 항의 수
trials = 100   # 시뮬레이션 횟수
seed = 42        # 재현성을 위한 시드 설정

# 시뮬레이션 실행
a_n_values = simulate_random_fibonacci(N, trials=trials, seed=seed)

# 그래프 그리기
plt.figure(figsize=(12, 8))
plt.plot(range(N+1), a_n_values, 'b-')
plt.title('Random Fibonacci Sequence: a_n vs n')
plt.xlabel('n')
plt.ylabel('a_n')
plt.grid(True)
plt.show()

# n 값과 a_n 값을 출력
print("n\ta_n")
print("-" * 20)
for n, a_n in enumerate(a_n_values):
    print(f"{n}\t{a_n:.6f}")
