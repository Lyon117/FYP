<?php
session_start();
if(isset($_SESSION["loggedin"]) != true) {
    header('Location: login.php');
    exit;
}
?>
<html>
<header>
<header>
<meta charseet="utf-8">
<title>Gp3_8 Database</title>
</header>
<body>
<h2>Welcome to Gp3_8 Locker System Database</h2>
<a href="logout.php">Logout</a>
</body>
</html>
