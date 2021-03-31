<?php
session_start();
if(isset($_SESSION["loggedin"]) != true) {
    header('Location: login.php');
    exit;
}
?>
<html>
<header>
    <meta charseet="utf-8">
    <title>Gp3_8 Database</title>
    <link rel="stylesheet" href="bootstrap.min.css">
    <script src="bootstrap.min.js"></script>
</header>
<body>
    <nav class="navbar navbar-default">
        <div class="container-fluid">
            <div class="navbar-header">
                <a class="navbar-brand" href="welcome.php">Gp3_8 Locker System Database</a>
            </div>
            <ul class="nav navbar-nav">
                <li class="nav-item">
                    <a href="usersregistration.php" class="nav-link">User registration</a>
                </li>
                <li class="nav-item">
                    <a href="historyrecord.php" class="nav-link">History record</a>
                </li>
            </ul>
        </div>
    </nav>

    <div class="container">
        <h2>Welcome to Gp3_8 Locker System Database</h2>
        
        <a href="logout.php">Logout</a>
    </div>
</body>
</html>
