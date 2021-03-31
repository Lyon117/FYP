<?php
session_start();
?>
<html>
    <head>
        <meta charset="utf-8">
        <title>Login Form</title>
        <link rel="stylesheet" href="login.css">
    </head>
    <style>
.tooltip {
    position: relative;
    display: inline-block;
    border-bottom: 1px dotted black;
}

.tooltip .tooltiptext {
    visibility: hidden;
    width: 400px;
    background-color: black;
    color: #fff;
    text-align: center;
    border-radius: 6px;
    padding: 30px 0;
    position: absolute;
    z-index: 1;
    bottom: 150%;
    left: -125%;
    margin-left: -20px;
}

.tooltip .tooltiptext::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: black transparent transparent transparent;
}

.tooltip:hover .tooltiptext {
    visibility: visible;
}

.tooltip2 {
    position: relative;
    display: inline-block;
    border-bottom: 1px dotted black;
}

.tooltip2 .tooltiptext {
    visibility: hidden;
    width: 400px;
    background-color: black;
    color: #fff;
    text-align: center;
    border-radius: 6px;
    padding: 30px 0;
    position: absolute;
    z-index: 1;
    bottom: 150%;
    left: -310%;
    margin-left: -20px;
}

.tooltip2 .tooltiptext::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: black transparent transparent transparent;
}

.tooltip2:hover .tooltiptext {
    visibility: visible;
}
</style>

    <body>
        <div class="container">
        
        <h1>Gp3_8 Locker System Database Website</h1>
        
        <form action="databaseconnect.php" method="post">
            <div class="tbox">
                <input type="text" name="username" placeholder="@username" value="">
            </div>        
            <div class="tbox">
                <input type="password" name="password" placeholder="password" value="">
            </div>
            <?php
        if(isset($_SESSION["errormessage"])) {
            $errormessage = $_SESSION["errormessage"];
            echo $errormessage;
        }
        ?>
            <input class="btn" type="submit" name="" value="LOG IN">
        
        </form>
        
        <div class="tooltip" bref="#"> WHERE IS IT? 
            <span class="tooltiptext">It is a website used for tracking locker system user's data,
            only authorized adminitrators are allowed to access the confidential data. 
            <br></br>
            Thank you for your cooperation.
            </span>
        </div>
        <br></br>
        
        <div class="tooltip2" bref="#"> HELP? 
            <span class="tooltiptext">You have to login with your authorized account to
            access the main pages.
            <br></br>
            If you do not have an account, please contact your coordinatetor.  
            </span>
        </div>
        
        </div>
        
        </body>
</html>
