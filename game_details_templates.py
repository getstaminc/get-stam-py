# MLB template rendering
mlb_template = """
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
        <title>Game Details</title>
        <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
        <style>
            body {
                background-color: #f9f9f9; /* Light background */
                font-family: 'Poppins', sans-serif;
                margin: 0;
                padding: 20px;
                color: #354050;
            }

            header {
                background-color: #007bff; /* Primary color */
                padding: 10px 20px;
                text-align: center;
                color: white;
            }

            nav a {
                color: white;
                text-decoration: none;
                margin: 0 10px;
                display: block;                  
            }

            h1 {
                margin: 20px 0;
            }

            h2 {
                margin-top: 30px;
            }

            table {
                width: 90%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }

            table, th, td {
                border: 1.5px solid #ddd;
            }

            th, td {
                padding: 4px;
                text-align: left;                 
            }

            th {
                background-color: #f2f2f2;
            }

            .green-bg {
                background-color: #7ebe7e;
                color: black;
            }

            .red-bg {
                background-color: #e35a69;
                color: black;
            }

            .grey-bg {
                background-color: #c6c8ca;
                color: black;
            }

            #gamesList {
                list-style-type: none;
                padding: 0;
            }
    
            .game-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                margin: 10px 0;
                background-color: #fff; /* Card background */
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }

            button, a {
                background-color: #007bff; /* Primary color */
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                text-decoration: none;
                transition: background-color 0.3s;
            }

            button:hover, a:hover {
                background-color: #0056b3; /* Darker shade on hover */
            }

            button:disabled {
                background-color: #cccccc; /* Light grey background */
                color: #666666; /* Dark grey text */
                cursor: not-allowed; /* Change cursor to not-allowed */
                opacity: 0.6; /* Reduce opacity */
            }

            /* Responsive Styles */
            @media only screen and (max-width: 600px) {
                body {
                    font-size: 14px;
                }
            }
            @media only screen and (min-width: 601px) and (max-width: 768px) {
                body {
                    font-size: 16px;
                }
            }
            @media only screen and (min-width: 769px) {
                body {
                    font-size: 18px;
                }
            }
            .info-icon {
                cursor: pointer;
                color: black; /* Color of the info icon */
                margin-left: 1px; /* Space between title and icon */
                padding: 1px;
                border: 1px solid black; /* Border color */
                border-radius: 50%; /* Makes the icon circular */
                width: 10px; /* Width of the icon */
                height: 10px; /* Height of the icon */
                display: inline-flex; /* Allows for centering */
                align-items: center; /* Center content vertically */
                justify-content: center; /* Center content horizontally */
                font-size: 14px; /* Font size of the "i" */
            }

            .info-icon:hover::after {
                content: attr(title);
                position: absolute;
                background: #fff;
                border: 1px solid #ccc;
                padding: 5px;
                border-radius: 4px;
                white-space: nowrap;
                z-index: 10;
                top: 20px; /* Adjust as needed */
                left: 0;
                box-shadow: 0 0 10px rgba(0,0,0,0.2);
            }               
            .color-keys {
                margin: 20px 0;
                padding: 15px;
                border: 1px solid #ddd;
                background-color: #f9f9f9;
            }

            .color-key h2 {
                margin: 0 0 10px;
            }

            .color-key table {
                width: 100%;
                border-collapse: collapse;
            }

            .color-key th, .color-key td {
                padding: 8px;
                text-align: left;
                border: 1px solid #ccc;
            }

            .color-key th {
                background-color: #f2f2f2;
            }
            .color-key {
                display: none; /* Hide by default */
                background-color: #f9f9f9; /* Background color for the key */
                border: 1px solid #ccc; /* Border for the key */
                padding: 5px;
                position: absolute; /* Position it relative to the header */
                z-index: 10; /* Ensure it appears above other elements */
            }

            th {
                position: relative; /* Needed for absolute positioning of the color key */
            }

            th:hover .color-key {
                display: block; /* Show the key on hover */
            }                      
            
        </style>

    </head>
    <body>
            <header>
            <nav>
                <a href="/">Home</a>
            </nav>
        </header>                         
        <h1>Game Details</h1>
        <table >
            <tr>
                <th>Home Team</th>
                <td>{{ game.homeTeam }}</td>
            </tr>
            <tr>
                <th>Away Team</th>
                <td>{{ game.awayTeam }}</td>
            </tr>
            <tr>
                <th>Home Score</th>
                <td>{{ game.homeScore }}</td>
            </tr>
            <tr>
                <th>Away Score</th>
                <td>{{ game.awayScore }}</td>
            </tr>
            <tr>
                <th>Odds</th>
                <td>{{ game.oddsText.replace('\n', '<br>')|safe }}</td>
            </tr>
            <tr>
                <th>Starting Pitchers</th>
                <td colspan="2">
                    Away: {{ away_pitcher }} ({{ away_stats }}) vs Home: {{ home_pitcher }} ({{ home_stats }})
                </td>
            </tr>
        </table>
                                    
                                    
        
        <h2>Last 5 Games - {{ game.homeTeam }}</h2>
        {% if home_team_last_5 %}
            <div class="game-card">                       
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Site</th>
                        <th>Team <span class="info-icon">i</span>
                            <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Team won</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Team lost</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>       
                        </th>
                        <th>Runs <span class="info-icon">i</span>
                        
                            <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Team won</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Team lost</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>      
                        </th>
                        <th>Line</th>
                        <th>Opponent</th>
                        <th>Opponent Runs</th>
                        <th>Total <span class="info-icon">i</span>
                                <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Total went over</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Total went under</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: grey;">&nbsp;</td>
                                                    <td>Push (tie with total)</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>     
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {% for game in home_team_last_5 %}
                        {% set is_total_exceeded, total_class = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                        {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['team'] }}
                            </td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['runs'] }}
                            </td>
                            <td>{{ game['line'] }}</td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:runs'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
            </div>                        
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}
        
        <h2>Last 5 Games - {{ game.awayTeam }}</h2>
        {% if away_team_last_5 %}
            <div class="game-card">                        
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Site</th>
                        <th>Team <span class="info-icon">i</span>
                            <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Team won</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Team lost</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>       
                        </th>
                        <th>Runs <span class="info-icon">i</span>
                            <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Team won</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Team lost</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>      
                        </th>
                        <th>Line</th>
                        <th>Opponent</th>
                        <th>Opponent Runs</th>
                        <th>Total <span class="info-icon">i</span>
                                <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Total went over</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Total went under</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: grey;">&nbsp;</td>
                                                    <td>Push (tie with total)</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>     
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {% for game in away_team_last_5 %}
                        {% set is_total_exceeded, total_class = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                        {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['team'] }}
                            </td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['runs'] }}
                            </td>             
                            <td>{{ game['line'] }}</td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:runs'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
            </div>                        
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}
        
        <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
        {% if last_5_vs_opponent %}
            <div class="game-card">                       
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Site</th>
                        <th>Team <span class="info-icon">i</span>
                            <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Team won</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Team lost</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>       
                        </th>
                        <th>Runs <span class="info-icon">i</span>
                            <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Team won</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Team lost</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>      
                        </th>
                        <th>Line</th>
                        <th>Opponent</th>
                        <th>Opponent Runs</th>
                        <th>Total <span class="info-icon">i</span>
                                <span class="color-key">
                                    <div class="color-keys">
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Color</th>
                                                    <th>Meaning</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td style="background-color: green;">&nbsp;</td>
                                                    <td>Total went over</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: red;">&nbsp;</td>
                                                    <td>Total went under</td>
                                                </tr>
                                                <tr>
                                                    <td style="background-color: grey;">&nbsp;</td>
                                                    <td>Push (tie with total)</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div> 
                            </span>     
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {% for game in last_5_vs_opponent %}
                        {% set is_total_exceeded, total_class = mlb_totals(game.get('runs', 0), game.get('o:runs', 0), game.get('total', 0)) %}
                        {% set is_winner = mlb_winner(game.get('runs', 0), game.get('o:runs', 0)) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['team'] }}
                            </td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['runs'] }}
                            </td>
                            <td>{{ game['line'] }}</td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:runs'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
            </div>                        
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}
    </body>
    </html>
"""
# NHL template rendering
nhl_template = """
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
        <title>Game Details</title>
        <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
        <style>
                body {
                    background-color: #f9f9f9; /* Light background */
                    font-family: 'Poppins', sans-serif;
                    margin: 0;
                    padding: 20px;
                    color: #354050;
                }

                header {
                    background-color: #007bff; /* Primary color */
                    padding: 10px 20px;
                    text-align: center;
                    color: white;
                }

                nav a {
                    color: white;
                    text-decoration: none;
                    margin: 0 10px;
                    display: block;                  
                }

                h1 {
                    margin: 20px 0;
                }

                h2 {
                    margin-top: 30px;
                }

                table {
                    width: 90%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }

                table, th, td {
                    border: 1.5px solid #ddd;
                }

                th, td {
                    padding: 4px;
                    text-align: left;                 
                }

                th {
                    background-color: #f2f2f2;
                }

                .green-bg {
                    background-color: #7ebe7e;
                    color: black;
                }

                .red-bg {
                    background-color: #e35a69;
                    color: black;
                }

                .grey-bg {
                    background-color: #c6c8ca;
                    color: black;
                }

                #gamesList {
                    list-style-type: none;
                    padding: 0;
                }
        
                .game-card {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 10px 0;
                    background-color: #fff; /* Card background */
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                }
                                        
                button:disabled {
                    background-color: #cccccc; /* Light grey background */
                    color: #666666; /* Dark grey text */
                    cursor: not-allowed; /* Change cursor to not-allowed */
                    opacity: 0.6; /* Reduce opacity */
                }

                button, a {
                    background-color: #007bff; /* Primary color */
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px 15px;
                    text-decoration: none;
                    transition: background-color 0.3s;
                }

                button:hover, a:hover {
                    background-color: #0056b3; /* Darker shade on hover */
                }

                /* Responsive Styles */
                @media only screen and (max-width: 600px) {
                    body {
                        font-size: 14px;
                    }
                }
                @media only screen and (min-width: 601px) and (max-width: 768px) {
                    body {
                        font-size: 16px;
                    }
                }
                @media only screen and (min-width: 769px) {
                    body {
                        font-size: 18px;
                    }
                }
                .info-icon {
                    cursor: pointer;
                    color: black; /* Color of the info icon */
                    margin-left: 1px; /* Space between title and icon */
                    padding: 1px;
                    border: 1px solid black; /* Border color */
                    border-radius: 50%; /* Makes the icon circular */
                    width: 10px; /* Width of the icon */
                    height: 10px; /* Height of the icon */
                    display: inline-flex; /* Allows for centering */
                    align-items: center; /* Center content vertically */
                    justify-content: center; /* Center content horizontally */
                    font-size: 14px; /* Font size of the "i" */
                }

                .info-icon:hover::after {
                    content: attr(title);
                    position: absolute;
                    background: #fff;
                    border: 1px solid #ccc;
                    padding: 5px;
                    border-radius: 4px;
                    white-space: nowrap;
                    z-index: 10;
                    top: 20px; /* Adjust as needed */
                    left: 0;
                    box-shadow: 0 0 10px rgba(0,0,0,0.2);
                }               
                .color-keys {
                    margin: 20px 0;
                    padding: 15px;
                    border: 1px solid #ddd;
                    background-color: #f9f9f9;
                }

                .color-key h2 {
                    margin: 0 0 10px;
                }

                .color-key table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .color-key th, .color-key td {
                    padding: 8px;
                    text-align: left;
                    border: 1px solid #ccc;
                }

                .color-key th {
                    background-color: #f2f2f2;
                }
                .color-key {
                    display: none; /* Hide by default */
                    background-color: #f9f9f9; /* Background color for the key */
                    border: 1px solid #ccc; /* Border for the key */
                    padding: 5px;
                    position: absolute; /* Position it relative to the header */
                    z-index: 10; /* Ensure it appears above other elements */
                }

                th {
                    position: relative; /* Needed for absolute positioning of the color key */
                }

                th:hover .color-key {
                    display: block; /* Show the key on hover */
                }                      
                
            </style>
    </head>
    <body>
        <header>
                <nav>
                    <a href="/">Home</a>
                </nav>
            </header>                               
        <h1>Game Details</h1>
        <table>
            <tr>
                <th>Home Team</th>
                <td>{{ game.homeTeam }}</td>
            </tr>
            <tr>
                <th>Away Team</th>
                <td>{{ game.awayTeam }}</td>
            </tr>
            <tr>
                <th>Home Score</th>
                <td>{{ game.homeScore }}</td>
            </tr>
            <tr>
                <th>Away Score</th>
                <td>{{ game.awayScore }}</td>
            </tr>
            <tr>
                <th>Odds</th>
                <td>{{ game.oddsText.replace('\n', '<br>')|safe }}</td>
            </tr>
        </table>
        <div><p>Hover over column titles for color meanings</p></div>
        <h2>Last 5 Games - {{ game.homeTeam }}</h2>
        {% if home_team_last_5 %}
            <table>
                <thead>
                    <tr>
                            <th>Date</th>
                            <th>Site</th>
                            <th>Team <span class="info-icon">i</span>
                                <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>       
                            </th>
                            <th>Goals <span class="info-icon">i</span>
                                <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>      
                            </th>
                            <th>Line</th>
                            <th>Opponent</th>
                            <th>Opponent Goals</th>
                            <th>Total <span class="info-icon">i</span>
                                    <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Total went over</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Total went under</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Push (tie with total)</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>     
                            </th>
                        </tr>
                </thead>
                <tbody>
                    {% for game in home_team_last_5 %}
                        {% set is_total_exceeded, total_class = nhl_totals(game.get('goals', 0), game.get('o:goals', 0), game.get('total', 0)) %}
                        {% set is_winner = nhl_winner(game.get('goals', 0), game.get('o:goals', 0)) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['team'] }}
                            </td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['goals'] }}
                            </td>
                            <td>{{ game['line'] }}</td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:goals'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}

        <h2>Last 5 Games - {{ game.awayTeam }}</h2>
        {% if away_team_last_5 %}
            <table>
                <thead>
                    <tr>
                            <th>Date</th>
                            <th>Site</th>
                            <th>Team <span class="info-icon">i</span>
                                <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>       
                            </th>
                            <th>Goals <span class="info-icon">i</span>
                                <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>      
                            </th>
                            <th>Line</th>
                            <th>Opponent</th>
                            <th>Opponent Goals</th>
                            <th>Total <span class="info-icon">i</span>
                                    <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Total went over</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Total went under</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Push (tie with total)</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>     
                            </th>
                        </tr>
                </thead>
                <tbody>
                    {% for game in away_team_last_5 %}
                        {% set is_total_exceeded, total_class = nhl_totals(game.get('goals', 0), game.get('o:goals', 0), game.get('total', 0)) %}
                        {% set is_winner = nhl_winner(game.get('goals', 0), game.get('o:goals', 0)) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['team'] }}
                            </td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['goals'] }}
                            </td>
                            <td>{{ game['line'] }}</td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:goals'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}

        <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
        {% if last_5_vs_opponent %}
            <table>
                <thead>
                    <tr>
                            <th>Date</th>
                            <th>Site</th>
                            <th>Team <span class="info-icon">i</span>
                                <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>       
                            </th>
                            <th>Goals <span class="info-icon">i</span>
                                <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>      
                            </th>
                            <th>Line</th>
                            <th>Opponent</th>
                            <th>Opponent Goals</th>
                            <th>Total <span class="info-icon">i</span>
                                    <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Total went over</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Total went under</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Push (tie with total)</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>     
                            </th>
                        </tr>
                </thead>
                <tbody>
                    {% for game in last_5_vs_opponent %}
                        {% set is_total_exceeded, total_class = nhl_totals(game.get('goals', 0), game.get('o:goals', 0), game.get('total', 0)) %}
                        {% set is_winner = nhl_winner(game.get('goals', 0), game.get('o:goals', 0)) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['team'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['goals'] }}</td>             
                            <td>{{ game['line'] }}</td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:goals'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}
    </body>
    </html>
"""
# Other sports template rendering
others_template = """
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
        <title>Game Details</title>
        <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
        <style>
                body {
                    background-color: #f9f9f9; /* Light background */
                    font-family: 'Poppins', sans-serif;
                    margin: 0;
                    padding: 20px;
                    color: #354050;
                }

                header {
                    background-color: #007bff; /* Primary color */
                    padding: 10px 20px;
                    text-align: center;
                    color: white;
                    border-radius: 5px;                     
                }

                nav a {
                    color: white;
                    text-decoration: none;
                    margin: 0 10px;
                    display: block;                     
                }

                h1 {
                    margin: 20px 0;
                }

                h2 {
                    margin-top: 30px;
                }

                table {
                    width: 90%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }

                table, th, td {
                    border: 1.5px solid #ddd;
                }

                th, td {
                    padding: 4px;
                    text-align: left;                 
                }

                th {
                    background-color: #f2f2f2;
                }

                .green-bg {
                    background-color: #7ebe7e;
                    color: black;
                }

                .red-bg {
                    background-color: #e35a69;
                    color: black;
                }

                .grey-bg {
                    background-color: #c6c8ca;
                    color: black;
                }

                #gamesList {
                    list-style-type: none;
                    padding: 0;
                }
        
                .game-card {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 10px 0;
                    background-color: #fff; /* Card background */
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                }
                
                button:disabled {
                    background-color: #cccccc; /* Light grey background */
                    color: #666666; /* Dark grey text */
                    cursor: not-allowed; /* Change cursor to not-allowed */
                    opacity: 0.6; /* Reduce opacity */
                }

                button, a {
                    background-color: #007bff; /* Primary color */
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px 15px;
                    text-decoration: none;
                    transition: background-color 0.3s;
                }

                button:hover, a:hover {
                    background-color: #0056b3; /* Darker shade on hover */
                }
                .info-icon {
                    cursor: pointer;
                    color: black; /* Color of the info icon */
                    margin-left: 1px; /* Space between title and icon */
                    padding: 1px;
                    border: 1px solid black; /* Border color */
                    border-radius: 50%; /* Makes the icon circular */
                    width: 10px; /* Width of the icon */
                    height: 10px; /* Height of the icon */
                    display: inline-flex; /* Allows for centering */
                    align-items: center; /* Center content vertically */
                    justify-content: center; /* Center content horizontally */
                    font-size: 14px; /* Font size of the "i" */
                }

                .info-icon:hover::after {
                    content: attr(title);
                    position: absolute;
                    background: #fff;
                    border: 1px solid #ccc;
                    padding: 5px;
                    border-radius: 4px;
                    white-space: nowrap;
                    z-index: 10;
                    top: 20px; /* Adjust as needed */
                    left: 0;
                    box-shadow: 0 0 10px rgba(0,0,0,0.2);
                }                         
                                            
                .color-keys {
                    margin: 20px 0;
                    padding: 15px;
                    border: 1px solid #ddd;
                    background-color: #f9f9f9;
                }

                .color-key h2 {
                    margin: 0 0 10px;
                }

                .color-key table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .color-key th, .color-key td {
                    padding: 8px;
                    text-align: left;
                    border: 1px solid #ccc;
                }

                .color-key th {
                    background-color: #f2f2f2;
                }
                .color-key {
                    display: none; /* Hide by default */
                    background-color: #f9f9f9; /* Background color for the key */
                    border: 1px solid #ccc; /* Border for the key */
                    padding: 5px;
                    position: absolute; /* Position it relative to the header */
                    z-index: 10; /* Ensure it appears above other elements */
                }

                th {
                    position: relative; /* Needed for absolute positioning of the color key */
                }

                th:hover .color-key {
                    display: block; /* Show the key on hover */
                }                         

                /* Responsive Styles */
                @media only screen and (max-width: 600px) {
                    body {
                        font-size: 14px;
                    }
                }
                @media only screen and (min-width: 601px) and (max-width: 768px) {
                    body {
                        font-size: 16px;
                    }
                }
                @media only screen and (min-width: 769px) {
                    body {
                        font-size: 18px;
                    }
                }
                .ranking-section {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: center;
                    gap: 2rem;
                    margin-top: 2rem;
                }

                .ranking-card {
                    width: 100%;
                    max-width: 350px;
                    flex: 1 1 300px;
                    background-color: #fff;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.07);
                    overflow: hidden;
                }

                .ranking-title {
                    text-align: center;
                    font-size: 1.1rem;
                    font-weight: 600;
                    padding: 1rem 0;
                    background-color: #f4f6f8;
                    color: #222;
                    border-bottom: 1px solid #e0e0e0;
                }

                .ranking-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: 'Segoe UI', sans-serif;
                }

                .ranking-table th,
                .ranking-table td {
                    padding: 10px 8px;
                    font-size: 0.85rem;
                    text-align: left;
                    border-bottom: 1px solid #f1f1f1;
                }

                .ranking-table th {
                    background-color: #fafafa;
                    color: #333;
                    font-weight: 600;
                }

                .ranking-subtext {
                    display: block;
                    font-size: 0.7rem;
                    color: #888;
                    margin-top: 2px;
                }

                @media (max-width: 768px) {
                    .ranking-section {
                        flex-direction: column;
                        gap: 1.5rem;
                    }

                    .ranking-card {
                        max-width: 100%;
                    }
                }
            </style>
    </head>
    <body>
        <header>
            <nav>
            <a href="/">Home</a>
            </nav>
        </header> 
        <h1>Game Details</h1>
        <table>
            <tr>
                <th>Home Team</th>
                <td>{{ game.homeTeam }}</td>
            </tr>
            <tr>
                <th>Away Team</th>
                <td>{{ game.awayTeam }}</td>
            </tr>
            <tr>
                <th>Home Score</th>
                <td>{{ game.homeScore }}</td>
            </tr>
            <tr>
                <th>Away Score</th>
                <td>{{ game.awayScore }}</td>
            </tr>
            <tr>
                <th>Odds</th>
                <td>{{ game.oddsText.replace('\n', '<br>')|safe }}</td>
            </tr>
        </table>

        {% if home_offense and home_defense and away_offense and away_defense %}
            {% set stat_map = {
                'Total': 'Total (Yds/G)',
                'Passing': 'Passing (Yds/G)',
                'Rushing': 'Rushing (Yds/G)',
                'Scoring': 'Scoring (Pts/G)'
            } %}

            <div class="ranking-section">
                <!-- Home Team -->
                <div class="ranking-card">
                    <div class="ranking-title">{{ game.homeTeam }} Rankings</div>
                    <table class="ranking-table">
                        <tr>
                            <th>Category</th><th>Offense</th><th>Defense</th>
                        </tr>
                        {% for label, key in stat_map.items() %}
                        <tr>
                            <td>{{ label }}</td>
                            <td>
                                {{ home_offense.get(key + ' Rank', '–') }}
                                <span class="ranking-subtext">{{ home_offense.get(key, '–') }}</span>
                            </td>
                            <td>
                                {{ home_defense.get(key + ' Rank', '–') }}
                                <span class="ranking-subtext">{{ home_defense.get(key, '–') }}</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>

                <!-- Away Team -->
                <div class="ranking-card">
                    <div class="ranking-title">{{ game.awayTeam }} Rankings</div>
                    <table class="ranking-table">
                        <tr>
                            <th>Category</th><th>Offense</th><th>Defense</th>
                        </tr>
                        {% for label, key in stat_map.items() %}
                        <tr>
                            <td>{{ label }}</td>
                            <td>
                                {{ away_offense.get(key + ' Rank', '–') }}
                                <span class="ranking-subtext">{{ away_offense.get(key, '–') }}</span>
                            </td>
                            <td>
                                {{ away_defense.get(key + ' Rank', '–') }}
                                <span class="ranking-subtext">{{ away_defense.get(key, '–') }}</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
        {% endif %}



        <h2>Last 5 Games - {{ game.homeTeam }}</h2>
        {% if home_team_last_5 %}
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Site</th>
                        <th>Team <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                        <th>Points <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>                 
                        <th>Spread <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Spread was covered</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Spread was not covered</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Spread was a push</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                        <th>Opponent</th>
                        <th>Opponent Points</th>
                        <th>Total <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Total went over</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Total went under</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Push (tie with total)</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {% for game in home_team_last_5 %}
                        {% set is_total_exceeded, total_class = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                        {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                        {% set line_win, line_class = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}                 
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['team'] }}
                            </td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['points'] }}
                            </td>
                            <td class="{{ line_class }}">
                                {{ game['line'] }}
                            </td>             
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:points'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}

        <h2>Last 5 Games - {{ game.awayTeam }}</h2>
        {% if away_team_last_5 %}
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Site</th>
                        <th>Team <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                        <th>Points <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>                 
                        <th>Spread <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Spread was covered</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Spread was not covered</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Spread was a push</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                        <th>Opponent</th>
                        <th>Opponent Points</th>
                        <th>Total <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Total went over</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Total went under</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Push (tie with total)</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {% for game in away_team_last_5 %}
                        {% set is_total_exceeded, total_class = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                        {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                        {% set line_win, line_class = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['team'] }}
                            </td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">
                                {{ game['points'] }}
                            </td>             
                            <td class="{{ line_class }}">
                                {{ game['line'] }}
                            </td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:points'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}

        <h2>Last 5 Games Between {{ game.homeTeam }} and {{ game.awayTeam }}</h2>
        {% if last_5_vs_opponent %}
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Site</th>
                        <th>Team <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>can I
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                        <th>Points <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Team won</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Team lost</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>                 
                        <th>Spread <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Spread was covered</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Spread was not covered</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Spread was a push</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                        <th>Opponent</th>
                        <th>Opponent Points</th>
                        <th>Total <span class="info-icon">i</span>
                            <span class="color-key">
                                        <div class="color-keys">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>Color</th>
                                                        <th>Meaning</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td style="background-color: green;">&nbsp;</td>
                                                        <td>Total went over</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: red;">&nbsp;</td>
                                                        <td>Total went under</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="background-color: grey;">&nbsp;</td>
                                                        <td>Push (tie with total)</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div> 
                                </span>             
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {% for game in last_5_vs_opponent %}
                        {% set is_total_exceeded, total_class = other_totals(game.get('points', 0), game.get('o:points', 0), game.get('total', 0)) %}
                        {% set is_winner = other_winner(game.get('points', 0), game.get('o:points', 0)) %}
                        {% set line_win, line_class = calculate_line_result(game.get('points'), game.get('line'), game.get('o:points')) %}
                        <tr>
                            <td>{{ game['date'] }}</td>  <!-- Date will be formatted in the template -->
                            <td>{{ game['site'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['team'] }}</td>
                            <td class="{{ 'green-bg' if is_winner else 'red-bg' if is_winner == False else '' }}">{{ game['points'] }}</td>             
                            <td class="{{ line_class }}">
                                {{ game['line'] }}
                            </td>
                            <td>{{ game['o:team'] }}</td>
                            <td>{{ game['o:points'] }}</td>
                            <td class="{{ total_class }}">
                                {{ game['total'] }}
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p class="center">No data available.</p>
        {% endif %}
    </body>
    </html>
"""