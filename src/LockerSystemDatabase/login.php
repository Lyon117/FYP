<?php
session_start();
?>
<html>
<header>
    <meta charseet="utf-8">
    <title>Gp3_8 Database Login</title>
</header>
<body>
    <form action="databaseconnect.php" method="post">
        <h2>Login to Gp3_8 Locker System Database</h2>
        User Name:<br>
        <input type="text" name="username"><br>
        Password:<br>
        <input type="password" name="password"><br>
        <?php
        if(isset($_SESSION["errormessage"])) {
            $errormessage = $_SESSION["errormessage"];
            echo $errormessage;
        }
        ?>
        <br>
        <input type="submit" value="Login">
    </form>
</body>
</html>
