# Templates for specific sports
historical_template = """
                <html>
                <head>
                    <!-- Google tag (gtag.js) -->
                    <script async src="https://www.googletagmanager.com/gtag/js?id=G-578SDWQPSK"></script>
                    <script>
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());

                    gtag('config', 'G-578SDWQPSK');
                    </script> 
                    <script 
                        async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6546677374101814"
                        crossorigin="anonymous">
                    </script>                     
                    <title>Game Info</title>
                    <style>
                        table {
                            width: 50%;
                            border-collapse: collapse;
                        }
                        table, th, td {
                            border: 1.5px solid #ddd;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #f2f2f2;
                        }
                        .game-pair {
                            margin-bottom: 20px;
                        }
                    </style>
                </head>
                <body>
                    <h1>Game Information</h1>
                    {% if result %}
                        {% for pair in result %}
                            <div class="game-pair">
                                <table>
                                    <thead>
                                        <tr>
                                            {% for header in pair[0].keys() %}
                                                <th>{{ header }}</th>
                                            {% endfor %}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for game in pair %}
                                            <tr>
                                                {% for value in game.values() %}
                                                    <td>{{ value }}</td>
                                                {% endfor %}
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% endfor %}
                    {% else %}
                        <p>No data available</p>
                    {% endif %}
                </body>
                </html>
            """
default_template = """
                <html>
                <head>
                    <title>Game Info</title>
                    <script 
                        async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6546677374101814"
                        crossorigin="anonymous">
                    </script>
                    <style>
                        table {
                            width: 80%;
                            border-collapse: collapse;
                            margin-left: auto;
                            margin-right: auto;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #007bff;
                            color: white;
                        }
                        tr:nth-child(even) {
                            background-color: #d8ebff;
                        }
                        tr:nth-child(odd) {
                            background-color: #FFFFFF;
                        }
                        .odds-category {
                            margin-top: 10px;
                        }
                        .odds-category h4 {
                            margin-bottom: 5px;
                            color: #007bff;
                        }
                        .odds-category ul {
                            list-style-type: none;
                            padding: 0;
                        }
                        .center {
                            text-align: center;
                        }
                        
                    </style>
                </head>
                <body>
                    <h1 class="center">Game Information</h1>
                    {% if result %}
                        <table>
                            <thead>
                                <tr>
                                    <th>Home Team</th>
                                    <th>Away Team</th>
                                    <th>Home Score</th>
                                    <th>Away Score</th>
                                    <th>Odds</th>
                                    {% if sport_key not in excluded_sports %}
                                        <th>Details</th>
                                    {% endif %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for match in result %}
                                    <tr>
                                        <td>{{ match.homeTeam }}</td>
                                        <td>{{ match.awayTeam }}</td>
                                        <td>{{ match.awayScore }}</td>
                                        <td>{{ match.homeScore }}</td>
                                        <td>
                                            <div class="odds-category">
                                                <h4>H2H:</h4>
                                                <ul>
                                                    {% for odd in match.odds.h2h %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                                <h4>Spreads:</h4>
                                                <ul>
                                                    {% for odd in match.odds.spreads %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                                <h4>Totals:</h4>
                                                <ul>
                                                    {% for odd in match.odds.totals %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                            </div>
                                        </td>
                                        {% if sport_key not in excluded_sports %}
                                            <td>
                                                <a href="/game/{{ match.game_id }}?sport_key={{ sport_key }}&date={{ current_date }}" class="view-details">View Details</a>
                                            </td>
                                        {% endif %}
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% elif next_game_date %}
                        <p class="center">No games on this date. The next game is on {{ next_game_date['pretty_date'] }}.</p>
                        <p class="center"><a href="javascript:void(0);" onclick="goToNextGame('{{ next_game_date['commence_date'] }}')" class="button center">Go to Next Game</a></p>
                    {% else %}
                        <p class="center">No games on this date</p>
                    {% endif %}
                </body>
                </html>
            """  # Your current HTML table
baseball_template = """
                <html>
                <head>
                    <title>Game Info</title>
                    <script 
                        async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6546677374101814"
                        crossorigin="anonymous">
                    </script>
                    <style>
                        table {
                            width: 80%;
                            border-collapse: collapse;
                            margin-left: auto;
                            margin-right: auto;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #007bff;
                            color: white;
                        }
                        tr:nth-child(even) {
                            background-color: #d8ebff;
                        }
                        tr:nth-child(odd) {
                            background-color: #FFFFFF;
                        }
                        .odds-category {
                            margin-top: 10px;
                        }
                        .odds-category h4 {
                            margin-bottom: 5px;
                            color: #007bff;
                        }
                        .odds-category ul {
                            list-style-type: none;
                            padding: 0;
                        }
                        .center {
                            text-align: center;
                        }
                        
                    </style>
                </head>
                <body>
                    <h1 class="center">Game Information</h1>
                    {% if result %}
                        <table>
                            <thead>
                                <tr>
                                    <th>Home Team</th>
                                    <th>Away Team</th>
                                    <th>Home Score</th>
                                    <th>Away Score</th>
                                    <th>Odds</th>
                                    {% if sport_key not in excluded_sports %}
                                        <th>Details</th>
                                    {% endif %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for match in result %}
                                    <tr>
                                        <td>{{ match.homeTeam }}</td>
                                        <td>{{ match.awayTeam }}</td>
                                        <td>{{ match.awayScore }}</td>
                                        <td>{{ match.homeScore }}</td>
                                        <td>
                                            <div class="odds-category">
                                                <h4>H2H:</h4>
                                                <ul>
                                                    {% for odd in match.odds.h2h %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                                <h4>Totals:</h4>
                                                <ul>
                                                    {% for odd in match.odds.totals %}
                                                        <li>{{ odd }}</li>
                                                    {% endfor %}
                                                </ul>
                                                <h4>Pitchers:</h4>
                                                <ul>
                                                    {% if match.isToday %}
                                                        {% if match.homePitcher and match.awayPitcher %}
                                                            <li>{{ match.awayTeam }} - {{ match.awayPitcher }} ({{ match.awayPitcherStats }})</li>
                                                            <li>{{ match.homeTeam }} - {{ match.homePitcher }} ({{ match.homePitcherStats }})</li>
                                                        {% else %}
                                                            <li>No pitcher data available</li>
                                                        {% endif %}
                                                    {% else %}
                                                        <li>No pitcher data available</li>
                                                    {% endif %}
                                                </ul>
                                            </div>
                                        </td>
                                        {% if sport_key not in excluded_sports %}
                                            <td>
                                                <a href="/game/{{ match.game_id }}?sport_key={{ sport_key }}&date={{ current_date }}" class="view-details">View Details</a>
                                            </td>
                                        {% endif %}
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% elif next_game_date %}
                        <p class="center">No games on this date. The next game is on {{ next_game_date['pretty_date'] }}.</p>
                        <p class="center"><a href="javascript:void(0);" onclick="goToNextGame('{{ next_game_date['commence_date'] }}')" class="button center">Go to Next Game</a></p>
                    {% else %}
                        <p class="center">No games on this date</p>
                    {% endif %}
                </body>
                </html>
            """  # A version tailored for MLB
soccer_template = """
                <html>
                <head>
                    <title>Game Info</title>
                    <script 
                        async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6546677374101814"
                        crossorigin="anonymous">
                    </script>
                    <style>
                        table {
                            width: 80%;
                            border-collapse: collapse;
                            margin-left: auto;
                            margin-right: auto;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                        th {
                            background-color: #007bff;
                            color: white;
                        }
                        tr:nth-child(even) {
                            background-color: #d8ebff;
                        }
                        tr:nth-child(odd) {
                            background-color: #FFFFFF;
                        }
                        .odds-category {
                            margin-top: 10px;
                        }
                        .odds-category h4 {
                            margin-bottom: 5px;
                            color: #007bff;
                        }
                        .odds-category ul {
                            list-style-type: none;
                            padding: 0;
                        }
                        .center {
                            text-align: center;
                        }
                        
                    </style>
                </head>
                <body>
                    <h1 class="center">Game Information</h1>
                    {% if result %}
                        <table>
                            <thead>
                                <tr>
                                    <th>Home Team</th>
                                    <th>Away Team</th>
                                    <th>Home Score</th>
                                    <th>Away Score</th>
                                    <th>Odds</th>
                                    {% if sport_key not in excluded_sports %}
                                        <th>Details</th>
                                    {% endif %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for match in result %}
                                    <tr>
                                        <td>{{ match.homeTeam }}</td>
                                        <td>{{ match.awayTeam }}</td>
                                        <td>{{ match.awayScore }}</td>
                                        <td>{{ match.homeScore }}</td>
                                        <td>
                                            <div class="odds-category">
                                                {% if match.odds.h2h %}
                                                    <h4>H2H:</h4>
                                                    <ul>
                                                    {% for h2h in match.odds.h2h %}
                                                        <li>{{ h2h }}</li>
                                                    {% endfor %}
                                                    </ul>
                                                {% endif %}

                                                {% if match.odds.totals %}
                                                    <h4>Totals:</h4>
                                                    <ul>
                                                    {% for total in match.odds.totals %}
                                                        <li>{{ total }}</li>
                                                    {% endfor %}
                                                    </ul>
                                                {% endif %}

                                                {% if match.odds.spreads %}
                                                    <h4>Spreads:</h4>
                                                    <ul>
                                                    {% for spread in match.odds.spreads %}
                                                        <li>{{ spread }}</li>
                                                    {% endfor %}
                                                    </ul>
                                                {% endif %}
                                            </div>
                                        </td>
                                        {% if sport_key not in excluded_sports %}
                                            <td>
                                                <a href="/game/{{ match.game_id }}?sport_key={{ sport_key }}&date={{ current_date }}" class="view-details">View Details</a>
                                            </td>
                                        {% endif %}
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% elif next_game_date %}
                        <p class="center">No games on this date. The next game is on {{ next_game_date['pretty_date'] }}.</p>
                        <p class="center"><a href="javascript:void(0);" onclick="goToNextGame('{{ next_game_date['commence_date'] }}')" class="button center">Go to Next Game</a></p>
                    {% else %}
                        <p class="center">No games on this date</p>
                    {% endif %}
                </body>
                </html>
            """  # A version showing just H2H