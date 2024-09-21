import random
from itertools import combinations
import json

# 참가자 리스트
players = [f'Player_{i}' for i in range(1, 11)]

# 모든 경기 생성 (45경기)
matches = list(combinations(players, 2))

def simulate_games():
    # 초기 점수 및 승패 기록 초기화
    scores = {player: 0 for player in players}
    win_loss = {player: {'win': [], 'loss': []} for player in players}
    
    # 각 경기마다 승자 결정
    for match in matches:
        winner = random.choice(match)
        loser = match[0] if winner == match[1] else match[1]
        
        scores[winner] += 1
        win_loss[winner]['win'].append(loser)
        win_loss[loser]['loss'].append(winner)
    
    return scores, win_loss

def check_condition(scores):
    high_scorers = [player for player, score in scores.items() if score >= 8]
    return len(high_scorers) == 3, high_scorers

def generate_html(scores, win_loss, high_scorers, attempt):
    # 점수 분포 정렬
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # 노드 데이터 생성
    nodes = []
    for player, score in sorted_scores:
        node = {
            "id": player,
            "label": f"{player}\n{score}점",
            "shape": "circle",
            "color": {
                "background": "#FFD700" if score >= 8 else "#97C2FC",
                "border": "#2E8B57",
                "highlight": {
                    "background": "#FFD700" if score >= 8 else "#97C2FC",
                    "border": "#2E8B57"
                }
            },
            "font": {
                "color": "black",
                "size": 14,
                "bold": True
            }
        }
        nodes.append(node)
    
    # 간선 데이터 생성
    edges = []
    for winner, losers in win_loss.items():
        for loser in losers['win']:
            edge = {
                "from": winner,
                "to": loser,
                "arrows": "to",
                "color": {
                    "color": "#848484",
                    "highlight": "#848484"
                },
                "width": 1
            }
            edges.append(edge)
    
    # JSON 직렬화
    nodes_json = json.dumps(nodes, ensure_ascii=False, indent=4)
    edges_json = json.dumps(edges, ensure_ascii=False, indent=4)
    
    # HTML 템플릿
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>시뮬레이션 결과</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
            }}
            h1, h2 {{
                color: #2E8B57;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            .highlight {{
                background-color: #FFD700;
                font-weight: bold;
            }}
            .title {{
                background-color: #2E8B57;
                color: white;
                text-align: center;
                padding: 10px 0;
                margin-bottom: 20px;
            }}
            /* vis.js 네트워크 스타일 */
            #network {{
                width: 100%;
                height: 600px;
                border: 1px solid lightgray;
            }}
        </style>
        <!-- vis.js 최신 라이브러리 불러오기 -->
        <script type="text/javascript" src="https://unpkg.com/vis-network@9.4.0/dist/vis-network.min.js"></script>
        <link href="https://unpkg.com/vis-network@9.4.0/dist/vis-network.min.css" rel="stylesheet" type="text/css" />
    </head>
    <body>
        <div class="title">
            <h1>조건을 만족하는 시뮬레이션 결과</h1>
        </div>
        <p>시도 횟수: {attempt}</p>
        
        <h2>점수 분포</h2>
        <table>
            <tr>
                <th>플레이어</th>
                <th>점수</th>
            </tr>
    """
    
    # 점수 분포 표 생성
    for player, score in sorted_scores:
        if score >= 8:
            html_content += f"""
            <tr>
                <td class="highlight">{player}</td>
                <td class="highlight">{score}점</td>
            </tr>
            """
        else:
            html_content += f"""
            <tr>
                <td>{player}</td>
                <td>{score}점</td>
            </tr>
            """
    
    html_content += """
        </table>
        
        <h2>승패 기록</h2>
        <table>
            <tr>
                <th>플레이어</th>
                <th>승리</th>
                <th>패배</th>
            </tr>
    """
    
    # 승패 기록 표 생성
    for player in players:
        wins = ', '.join(win_loss[player]['win']) if win_loss[player]['win'] else '없음'
        losses = ', '.join(win_loss[player]['loss']) if win_loss[player]['loss'] else '없음'
        if scores[player] >= 8:
            html_content += f"""
            <tr>
                <td class="highlight">{player}</td>
                <td class="highlight">{wins}</td>
                <td class="highlight">{losses}</td>
            </tr>
            """
        else:
            html_content += f"""
            <tr>
                <td>{player}</td>
                <td>{wins}</td>
                <td>{losses}</td>
            </tr>
            """
    
    html_content += f"""
        </table>
        
        <h2>경기 결과 그래프</h2>
        <div id="network"></div>
        
        <script type="text/javascript">
            // 노드 및 간선 데이터 로드
            var nodes = new vis.DataSet({nodes_json});
            var edges = new vis.DataSet({edges_json});
            
            // 네트워크 데이터
            var data = {{
                nodes: nodes,
                edges: edges
            }};
            
            // 네트워크 옵션
            var options = {{
                layout: {{
                    improvedLayout: true,
                    hierarchical: false
                }},
                edges: {{
                    smooth: {{
                        type: 'cubicBezier',
                        forceDirection: 'horizontal',
                        roundness: 0.4
                    }},
                    arrows: {{
                        to: {{enabled: true, scaleFactor:1}}
                    }},
                    color: {{
                        color: '#848484',
                        highlight: '#848484'
                    }}
                }},
                physics: {{
                    stabilization: false,
                    barnesHut: {{
                        gravitationalConstant: -30000,
                        springLength: 250,
                        springConstant: 0.001
                    }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 200
                }}
            }};
            
            // 네트워크 생성
            var container = document.getElementById('network');
            var network = new vis.Network(container, data, options);
        </script>
    </body>
    </html>
    """
    
    # HTML 파일로 저장
    with open("simulation_result.html", "w", encoding="utf-8") as file:
        file.write(html_content)
    print("결과가 'simulation_result.html' 파일로 저장되었습니다.")

def main(max_attempts=100000):
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        scores, win_loss = simulate_games()
        condition_met, high_scorers = check_condition(scores)
        
        if condition_met:
            print(f"조건을 만족하는 시뮬레이션을 찾았습니다! (시도 횟수: {attempt})")
            generate_html(scores, win_loss, high_scorers, attempt)
            return
    
    # 조건을 만족하지 못한 경우 HTML로 저장
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>시뮬레이션 결과</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                text-align: center;
            }}
            .title {{
                background-color: #B22222;
                color: white;
                padding: 20px;
                margin-bottom: 20px;
            }}
            p {{
                font-size: 18px;
            }}
        </style>
    </head>
    <body>
        <div class="title">
            <h1>조건을 만족하는 시뮬레이션 결과가 없습니다.</h1>
        </div>
        <p>최대 시도 횟수({max_attempts}) 내에 조건을 만족하는 시뮬레이션 결과가 없습니다.</p>
    </body>
    </html>
    """
    with open("simulation_result.html", "w", encoding="utf-8") as file:
        file.write(html_content)
    print(f"최대 시도 횟수({max_attempts}) 내에 조건을 만족하는 시뮬레이션 결과가 없습니다. 'simulation_result.html' 파일을 확인하세요.")

# 시뮬레이션 실행
if __name__ == "__main__":
    main()
